"""Optional browser test: drives the real web app in Chromium against a live backend (stand-in Ollama).

One-time setup, with the backend venv active:
    pip install playwright
    playwright install chromium
Run (from the backend folder, venv active; quit the real Ollama app first - port 11434):
    python ../tests/e2e_browser.py
Screenshots are saved to tests/screenshots/.
"""
import os, re, subprocess, sys, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
BACKEND_PY = os.environ.get("BACKEND_PYTHON", sys.executable)   # python that has the backend packages
tmp = tempfile.mkdtemp()
env = dict(os.environ, DATA_DIR=f"{tmp}/data", DB_PATH=f"{tmp}/wb.db", ADMIN_USERNAME="admin",
           ADMIN_PASSWORD="test-pass", JWT_SECRET="s", TESSERACT_CMD="", VISION_MODEL="", MOCK_AGENT="")
fake = subprocess.Popen([BACKEND_PY, str(ROOT / "tests/fake_ollama.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
srv = subprocess.Popen([BACKEND_PY, "-m", "uvicorn", "app.main:app", "--port", "8000"], cwd=ROOT / "backend",
                       env=env, stdout=open(f"{tmp}/server.log", "w"), stderr=subprocess.STDOUT)
time.sleep(10)

passed = failed = 0
ROWS = None
def check(name, cond, extra=""):
    global passed, failed
    if cond: passed += 1; print("  PASS ", name)
    else: failed += 1; print("  FAIL ", name, extra)

SHOTS = str(ROOT / "tests" / "screenshots"); Path(SHOTS).mkdir(exist_ok=True)
console_errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1366, "height": 860}, accept_downloads=True)
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        DOCROWS = page.locator("section[aria-labelledby=docs-title] tbody tr")
        HISTROWS = page.locator("section[aria-labelledby=history-title] tbody tr")
        S = lambda n: page.screenshot(path=f"{SHOTS}/{n}.png")

        print("Login")
        page.goto("http://127.0.0.1:8000/")
        check("/ redirects to /ui/", "/ui/" in page.url, page.url)
        expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
        S("01_login")
        page.get_by_label("Username").fill("admin"); page.get_by_label("Password").fill("wrong")
        page.get_by_role("button", name="Sign in").click()
        expect(page.get_by_role("alert")).to_contain_text("not right")
        check("wrong password shows a clear message", True)
        page.get_by_label("Password").fill("test-pass"); page.get_by_role("button", name="Sign in").click()
        expect(page.get_by_role("heading", name="Ask your documents")).to_be_visible()
        check("login works", True)

        print("Ask: empty state")
        expect(page.get_by_text("You have not added any documents yet")).to_be_visible()
        check("no-documents notice shown", True)
        S("02_ask_empty")

        print("Documents")
        page.get_by_role("button", name="Documents", exact=True).click()
        files = [str(ROOT / "sample_docs" / f) for f in ["SOP_Pump_Maintenance.docx", "Inspection_Report_Pump_P101.png", "Inspection_Report_Pump_P101_scanned.pdf"]]
        page.set_input_files("#file-input", files)
        expect(page.locator(".upload-item.done")).to_have_count(3, timeout=60000)
        check("3 files uploaded and indexed", True)
        expect(DOCROWS).to_have_count(3)
        check("document table lists 3 files", True)
        check("added-by shown", page.locator("section[aria-labelledby=docs-title] tbody").inner_text().count("admin") >= 3)
        page.set_input_files("#file-input", {"name": "notes.exe", "mimeType": "application/octet-stream", "buffer": b"abc"})
        expect(page.get_by_text("This file type is not supported")).to_be_visible()
        check("unsupported type rejected in the browser", True)
        S("03_documents")
        page.get_by_role("button", name="Clear list").click()
        expect(page.locator(".upload-item")).to_have_count(0)
        check("Clear list empties the upload log", True)

        print("Ask")
        page.get_by_role("button", name="Ask", exact=True).click()
        page.get_by_role("button", name=re.compile("^The measured impeller wear")).click()
        check("example fills the box", "4.2 mm" in page.get_by_label("Your question").input_value())
        page.get_by_role("button", name="Ask", exact=True).last.click()
        expect(page.get_by_text("Reading your documents")).to_be_visible()
        check("thinking indicator while waiting", True)
        chip = page.locator("button.cite").first
        expect(chip).to_be_visible(timeout=60000)
        check("answer has clickable citation chips", True)
        expect(page.locator(".verdict")).to_be_visible()
        print("        verdict:", page.locator(".verdict").inner_text().replace("\n", " | "))
        expect(page.locator(".slip").first).to_be_visible()
        check("evidence slips shown beside the answer", True)
        chip.click()
        expect(page.locator(".slip.is-active")).to_have_count(1)
        check("clicking a citation highlights its source", True)
        S("04_ask_answer")
        page.get_by_text("How this was answered").click()
        check("tools listed (document search + calculator)", "calculator" in page.locator(".how").inner_text().lower() or "Used the calculator" in page.locator(".how").inner_text())
        with page.expect_download() as dl:
            page.get_by_role("button", name="Word").click()
        path = dl.value.path(); check("Word report downloads", Path(path).stat().st_size > 1500)
        with page.expect_download() as dl:
            page.get_by_role("button", name="PDF").click()
        check("PDF report downloads", Path(dl.value.path()).stat().st_size > 1500)

        print("Switching tabs keeps the thread")
        page.get_by_role("button", name="System", exact=True).click()
        expect(page.get_by_role("heading", name="System")).to_be_visible()
        expect(page.locator(".status-row")).to_have_count(5)
        check("system lists 5 checks", True)
        print("        ", page.locator(".status-list").inner_text().replace("\n", " / ")[:300])
        S("05_system")
        page.get_by_role("button", name="Ask", exact=True).click()
        check("thread still there after visiting another tab", page.locator(".turn").count() == 1)

        print("History")
        page.get_by_role("button", name="History", exact=True).click()
        expect(HISTROWS.first).to_be_visible()
        page.get_by_role("button", name="Open").first.click()
        expect(page.locator(".history-detail")).to_be_visible()
        check("history row opens with answer and sources", page.locator(".history-detail .slip").count() >= 1)
        check("history does not claim a verification it can't know", page.locator(".history-detail .verdict-ok").count() == 0)
        S("06_history")
        page.get_by_role("button", name="Uploads").click()
        expect(HISTROWS.first).to_be_visible()
        check("uploads filter lists the 3 uploads", HISTROWS.count() == 3)

        print("Remove a document")
        page.get_by_role("button", name="Documents", exact=True).click()
        page.get_by_role("button", name=re.compile("^Remove Inspection_Report_Pump_P101.png")).click()
        page.get_by_role("button", name="Yes, remove").click()
        expect(DOCROWS).to_have_count(2)
        check("document removed after confirmation", True)

        print("Reload keeps the session")
        page.reload()
        expect(page.get_by_role("heading", name="Ask your documents")).to_be_visible()
        check("still signed in after reload", True)
        check("thread restored after reload", page.locator(".turn").count() == 1)

        print("Phone-sized screen")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        S("07_mobile_ask")
        sw = page.evaluate("document.documentElement.scrollWidth"); check("no sideways scrolling at 390px", sw <= 392, f"scrollWidth={sw}")
        page.set_viewport_size({"width": 1366, "height": 860})

        print("Session expiry")
        page.evaluate("sessionStorage.setItem('enclave_token','garbage')")
        page.reload()
        expect(page.get_by_text("Your session ended")).to_be_visible(timeout=10000)
        check("expired/invalid token sends you back to sign in with a message", True)
        S("08_session_ended")

        print("Sign out")
        page.get_by_label("Username").fill("admin"); page.get_by_label("Password").fill("test-pass")
        page.get_by_role("button", name="Sign in").click()
        expect(page.get_by_role("heading", name="Ask your documents")).to_be_visible()
        page.get_by_role("button", name="Sign out").click()
        expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
        check("sign out works", True)
        b.close()
finally:
    real = [e for e in console_errors if "401" not in e]
    check("no unexpected browser console errors (expected 401s ignored)", not real, str(real[:3]))
    srv.terminate(); fake.terminate()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

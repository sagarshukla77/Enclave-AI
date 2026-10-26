import { useState } from "react";
import { api, setToken } from "../api.js";

export default function Login({ notice, onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api.login(username.trim(), password);
      setToken(res.access_token);
      onLogin();
    } catch (err) {
      setError(err.status === 401 ? "That username or password is not right." : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <form className="sheet login-sheet" onSubmit={submit}>
        <p className="wordmark">Enclave AI</p>
        <h1>Sign in</h1>
        <p className="lede">Your documents, questions and answers stay on this computer.</p>
        {notice && <p className="notice" role="status">{notice}</p>}
        <label className="field">
          <span>Username</span>
          <input type="text" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
        </label>
        <label className="field">
          <span>Password</span>
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="field-error" role="alert">{error}</p>}
        <button type="submit" className="btn primary wide" disabled={busy || !username || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

# Free Oracle Cloud deployment

This setup runs the web app, FastAPI backend, Ollama, and Caddy on one Oracle Cloud Always Free ARM VM. The VM has limited CPU, so model replies can take a while. Oracle may reclaim an Always Free VM that stays idle. Uploaded documents, the workbench database, Chroma index, and Ollama models are stored on the VM's persistent boot volume.

## 1. Create the VM

In Oracle Cloud, create an Always Free eligible Ubuntu ARM instance in your account's home region. Allocate up to 2 OCPUs and 12 GB RAM, and use a boot volume of about 100 GB (within the Always Free block storage allowance). Assign a public IPv4 address.

In the VM's subnet security list, allow inbound TCP 22 only from your own IP, and TCP 80 and 443 from the internet. Do not expose ports 8000 or 11434. Add matching host firewall rules after connecting by SSH.

## 2. Point a domain to the VM

Use a domain you control (a free subdomain provider is fine) and create an A record pointing to the VM's public IPv4 address. Wait until the record resolves before starting Caddy; Caddy obtains and renews HTTPS certificates automatically.

## 3. Install Docker and get the app

Connect to the VM over SSH, then run:

```sh
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Sign out and reconnect so the Docker group change takes effect. Then:

```sh
git clone https://github.com/sagarshukla77/Enclave-AI.git
cd Enclave-AI
cp deploy/oracle.env.example .env
```

Edit `.env`: set `DEPLOY_DOMAIN` to the domain's full hostname, choose a unique administrator password, and set a random JWT key. Generate a key with `openssl rand -hex 32` and paste its output as `JWT_SECRET`.

## 4. Start the app and download the models

```sh
docker compose up -d --build
docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
docker compose exec ollama ollama pull nomic-embed-text
```

The first build and model downloads can take a while on the free VM. Open `https://<your-domain>` after they finish and sign in with the administrator username and password from `.env`.

To check service status, run `docker compose ps`. To view app logs, run `docker compose logs -f app`.

## Storage and privacy

The Compose named volumes keep uploaded files, the SQLite database, Chroma index, Ollama models, and Caddy certificates across container rebuilds. They still live on the VM's boot volume; create Oracle volume backups before storing important documents. Anyone uploading a document to this hosted instance sends it to the Oracle VM. Keep `.env` private and never add it to Git.


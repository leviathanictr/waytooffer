# Deployment / GitHub Actions

Required GitHub repository secrets (Settings → Secrets → Actions):

- `SSH_PRIVATE_KEY` — private SSH key used by the workflow (PEM format). Add the corresponding public key to `/root/.ssh/authorized_keys` on the server.
- `SSH_HOST` — server IP or hostname (e.g., `93.88.203.98`).
- `SSH_PORT` — SSH port (e.g., `9714`).
- `SSH_USER` — SSH username (e.g., `root`).
- `DEPLOY_PATH` — optional path on server (default: `/root/waytooffer`).

How it works:

- Push to the `deploy` branch (or run the workflow manually via `workflow_dispatch`).
- The workflow uses the SSH key to connect to the server and runs the simple deploy steps:
  - clone repo (if needed) or reset to `origin/deploy`
  - run `docker compose up -d --build --remove-orphans`

Notes / initial server setup:

- The workflow expects Docker and the Docker Compose plugin to be installed on the server.
- TLS certificates are handled via the `certbot` service in `docker-compose.yml`. You need to ensure DNS for `waytooffer.ru` and `api.waytooffer.ru` points to the server before running the certbot initial command.
- For first-time setup I can SSH to the server (using the credentials you provided) and perform initial install, clone repo and run `docker compose up -d`. After that you can use the workflow for automatic deploys.

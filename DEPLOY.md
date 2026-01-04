# Production deployment notes

1. Copy `.env.production` to `.env` on the server and edit values (or set environment variables via systemd `EnvironmentFile`).

2. Create a Python virtual environment on the server, e.g. `/opt/faceapp/venv` and install dependencies:

```bash
python3 -m venv /opt/faceapp/venv
source /opt/faceapp/venv/bin/activate
pip install -r requirements.txt
```

3. Prepare directories and permissions (example):

```bash
sudo useradd -r -s /usr/sbin/nologin faceapp || true
sudo mkdir -p /opt/faceapp
sudo chown -R $USER:faceapp /opt/faceapp
mkdir -p /var/log/faceapp
```

4. Systemd service

Use the template `deploy/faceapp.service` (edit `WorkingDirectory`, `EnvironmentFile` and `ExecStart` to match your paths). Example `ExecStart` inside service file:

```
ExecStart=/opt/faceapp/venv/bin/gunicorn --workers ${GUNICORN_WORKERS:-3} --timeout 120 --bind ${GUNICORN_BIND:-127.0.0.1:8000} run:app
```

After creating the service file in `/etc/systemd/system/`, reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable faceapp.service
sudo systemctl start faceapp.service
sudo journalctl -u faceapp.service -f
```

5. Reverse proxy (NGINX)

Configure NGINX to proxy to `127.0.0.1:8000` and serve static files directly. See `deploy/nginx.conf` for an example.

Render.com
------------

To deploy on Render using the Git repo:

1. Commit and push this repository to GitHub/GitLab.
2. In Render dashboard, create a new **Web Service** and connect your repo/branch.
3. Set the **Build Command** to:

```bash
pip install -r requirements.txt
```

4. Set the **Start Command** to:

```bash
bash start.sh
```

5. In Render's Environment settings, add required secrets and env vars (do not store `.env` in repo):
- `SECRET_KEY`
- `MONGODB_URI`
- `MONGODB_DB`
- Any file path overrides like `UPLOAD_FOLDER`, `ENCODING_FILE`, `ATTENDANCE_DIR` (use absolute paths under `/tmp` or configure persistent disks if needed)

Notes:
- Render provides a `PORT` environment variable; `start.sh` binds Gunicorn to `0.0.0.0:$PORT`.
- For static/media persistence, use Render persistent disks or an external storage (S3) because the container filesystem is ephemeral.
- If you prefer, use the provided `render.yaml` to create the service via the Render dashboard/CLI.

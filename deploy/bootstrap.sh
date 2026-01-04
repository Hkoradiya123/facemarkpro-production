#!/usr/bin/env bash
set -euo pipefail

# FaceMak Pro EC2 bootstrap (Ubuntu 22.04)
# Usage: sudo bash deploy/bootstrap.sh <DOMAIN or PUBLIC_IP> <ENVIRONMENT=prod|staging>

DOMAIN_OR_IP=${1:-localhost}
ENVIRONMENT=${2:-prod}

echo "[1/8] Updating system packages"
apt-get update -y
apt-get upgrade -y
apt-get install -y \ 
  build-essential git curl wget unzip pkg-config \ 
  python3 python3-venv python3-pip \ 
  ffmpeg libgl1 libglib2.0-0 \ 
  nginx

echo "[2/8] Creating app user and directories"
id -u faceapp >/dev/null 2>&1 || useradd -m -s /bin/bash faceapp
mkdir -p /opt/faceapp
chown -R faceapp:faceapp /opt/faceapp

echo "[3/8] Deploying application code to /opt/faceapp"
# Expect repo already cloned to /opt/faceapp or copy current dir
if [ ! -f /opt/faceapp/run.py ]; then
  rsync -a --exclude .git --exclude venv --exclude __pycache__ ./ /opt/faceapp/
fi
chown -R faceapp:faceapp /opt/faceapp

echo "[4/8] Setting up Python virtual environment"
sudo -u faceapp bash -lc 'cd /opt/faceapp && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip wheel setuptools'
if [ -f /opt/faceapp/requirements.txt ]; then
  sudo -u faceapp bash -lc 'cd /opt/faceapp && source venv/bin/activate && pip install -r requirements.txt'
fi

echo "[5/8] Writing environment file"
cat >/opt/faceapp/.env <<EOF
ENVIRONMENT=${ENVIRONMENT}
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 16)
FACE_RECOGNITION_MODEL=buffalo_l
FACE_RECOGNITION_TOLERANCE=0.85
# Set your Mongo URI (Atlas recommended)
MONGODB_URI=
EOF
chown faceapp:faceapp /opt/faceapp/.env
chmod 600 /opt/faceapp/.env

echo "[6/8] Installing systemd service"
cat >/etc/systemd/system/faceapp.service <<'SERVICE'
[Unit]
Description=FaceMak Pro (Flask) via Gunicorn
After=network.target

[Service]
User=faceapp
Group=faceapp
WorkingDirectory=/opt/faceapp
EnvironmentFile=/opt/faceapp/.env
ExecStart=/opt/faceapp/venv/bin/gunicorn --workers 3 --timeout 120 --bind 127.0.0.1:8000 run:app
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable faceapp.service
systemctl restart faceapp.service

echo "[7/8] Configuring Nginx as reverse proxy"
cat >/etc/nginx/sites-available/faceapp.conf <<NGINX
server {
    listen 80;
    server_name ${DOMAIN_OR_IP};

    client_max_body_size 50M;

    location /static/ {
        alias /opt/faceapp/app/static/;
        access_log off;
        expires 30d;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180;
        proxy_connect_timeout 180;
        proxy_pass http://127.0.0.1:8000;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/faceapp.conf /etc/nginx/sites-enabled/faceapp.conf
rm -f /etc/nginx/sites-enabled/default || true
nginx -t
systemctl restart nginx

echo "[8/8] Optional: TLS with Let's Encrypt (run manually)"
echo "To enable HTTPS: apt-get install -y certbot python3-certbot-nginx && certbot --nginx -d ${DOMAIN_OR_IP}"

echo "Done. App should be reachable via http://${DOMAIN_OR_IP}" 


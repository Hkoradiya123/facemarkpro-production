EC2 Deployment Guide (FaceMak Pro)

Prerequisites
- Ubuntu 22.04 EC2 instance (t3.medium for CPU; g4dn.xlarge for GPU)
- Security Group: allow 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Elastic IP (recommended)

Steps
1) SSH to server
```
ssh ubuntu@YOUR_DOMAIN_OR_IP
```

2) Copy repo to server (if not using git directly)
```
sudo apt-get update -y && sudo apt-get install -y rsync
rsync -av --exclude .git ./ ubuntu@YOUR_DOMAIN_OR_IP:/home/ubuntu/app/
```

3) Run bootstrap
```
cd /home/ubuntu/app
sudo bash deploy/bootstrap.sh YOUR_DOMAIN_OR_IP prod
```

4) Set environment variables
Edit `/opt/faceapp/.env` and set `MONGODB_URI` (Atlas recommended) and any other secrets. Then restart service:
```
sudo systemctl restart faceapp
```

5) TLS (optional)
```
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

Service management
```
sudo systemctl status faceapp
sudo journalctl -u faceapp -f
sudo systemctl restart faceapp
```

Notes
- Gunicorn binds to 127.0.0.1:8000; Nginx proxies requests
- Static served from `/opt/faceapp/app/static/`
- Adjust workers/timeouts in the systemd ExecStart if needed


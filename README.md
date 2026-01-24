<div align="center">

# 🔐 CertDeliver

**Automated SSL Certificate Distribution Service**

[![CI](https://github.com/yuanweize/CertDeliver/actions/workflows/ci.yml/badge.svg)](https://github.com/yuanweize/CertDeliver/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL_v3-blue?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker/)

**[English](README.md)** · **[中文文档](README_CN.md)**

---

*Securely distribute Let's Encrypt certificates to multiple servers with zero manual intervention.*

</div>

## 📖 Overview

CertDeliver automates the distribution of SSL certificates from a central server to multiple client machines. When certbot renews your certificates, CertDeliver packages them and makes them available for clients to download automatically.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Certbot       │────▶│  CertDeliver    │────▶│   Client 1      │
│   (renewal)     │     │  Server         │     │   (nginx/xray)  │
└─────────────────┘     └─────────────────┘     ├─────────────────┤
                                                │   Client 2      │
                                                │   (nginx/xray)  │
                                                └─────────────────┘
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 **Secure Auth** | Constant-time token comparison prevents timing attacks |
| 🌐 **IP Whitelist** | DNS-based client verification |
| 📦 **Auto Package** | Certbot hook bundles certs automatically |
| 🔄 **Auto Sync** | Clients poll and update certs automatically |
| 🐳 **Docker Ready** | One-command deployment with Docker Compose |
| ⚡ **Modern Stack** | Python 3.10+, FastAPI, Pydantic, Type Hints |

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Certbot (for certificate generation)
- Linux server (Debian/Ubuntu or RHEL/CentOS)

### Installation

```bash
# Clone the repository
git clone https://github.com/yuanweize/CertDeliver.git
cd CertDeliver

# Install with pip
pip install .

# Or run installer script
sudo bash scripts/install.sh
```

### Docker Deployment

```bash
cd docker
cp ../.env.example .env
# Edit .env with your settings
docker compose up -d
```

## ⚙️ Configuration

CertDeliver uses environment variables for configuration. Create a `.env` file:

```bash
# Server Configuration
CERTDELIVER_TOKEN=your-secure-random-token
CERTDELIVER_DOMAIN_LIST=client1.example.com,client2.example.com
CERTDELIVER_PORT=8000
CERTDELIVER_TARGETS_DIR=/opt/CertDeliver/targets

# Client Configuration
CERTDELIVER_CLIENT_SERVER_URL=https://cert.example.com/api/v1/
CERTDELIVER_CLIENT_TOKEN=your-secure-random-token
CERTDELIVER_CLIENT_CERT_NAME=cert
CERTDELIVER_CLIENT_CERT_DEST_PATH=/etc/ssl/certs
CERTDELIVER_CLIENT_POST_UPDATE_COMMAND=systemctl reload nginx
```

> 📄 See [config/.env.example](config/.env.example) for all available options.

## 📦 Server Setup

### 1. Configure Certbot

```bash
# Example with Aliyun DNS plugin
certbot certonly \
  -a dns-aliyun \
  --certbot-dns-aliyun:dns-aliyun-credentials /etc/letsencrypt/dns-key \
  -d "*.example.com" \
  --cert-name cert
```

### 2. Setup Renewal Hook

```bash
# Add to crontab
crontab -e

# Add this line:
0 0,12 * * * certbot renew -q --post-hook "certdeliver-hook"
```

### 3. Start Server

```bash
# Option 1: Direct run
certdeliver-server

# Option 2: Systemd service
sudo cp CertDeliver.service /etc/systemd/system/
sudo systemctl enable --now certdeliver

# Option 3: Docker
cd docker && docker compose up -d
```

### 4. Reverse Proxy (Recommended)

```nginx
server {
    listen 443 ssl http2;
    server_name cert.example.com;

    ssl_certificate     /etc/letsencrypt/live/cert/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cert/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📱 Client Setup

### 1. Install

```bash
pip install git+https://github.com/yuanweize/CertDeliver.git
```

### 2. Configure Environment

```bash
export CERTDELIVER_CLIENT_SERVER_URL="https://cert.example.com/api/v1/"
export CERTDELIVER_CLIENT_TOKEN="your-token"
export CERTDELIVER_CLIENT_CERT_NAME="cert"
export CERTDELIVER_CLIENT_CERT_DEST_PATH="/etc/nginx/ssl"
export CERTDELIVER_CLIENT_POST_UPDATE_COMMAND="systemctl reload nginx"
```

### 3. Setup Cron

```bash
# Check for updates twice daily
crontab -e

# Add:
30 6,18 * * * certdeliver-client >> /var/log/certdeliver.log 2>&1
```

## 📁 Project Structure

```
CertDeliver/
├── src/certdeliver/           # Source code
│   ├── config.py              # Configuration (Pydantic)
│   ├── server/                # FastAPI server
│   │   ├── app.py             # Application entry
│   │   ├── routes.py          # API endpoints
│   │   ├── auth.py            # Authentication
│   │   └── whitelist.py       # IP whitelist
│   ├── client/                # Certificate downloader
│   │   └── downloader.py
│   └── hooks/                 # Certbot hooks
│       └── certbot_hook.py
├── tests/                     # Unit tests
├── docker/                    # Docker deployment
├── config/                    # Configuration examples
├── scripts/                   # Installation scripts
├── pyproject.toml             # Package configuration
└── README.md
```

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info and client IP |
| `/health` | GET | Health check for monitoring |
| `/api/v1/{file}` | GET | Download/check certificate |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | ✅ | Authentication token |
| `download` | bool | ❌ | Force download mode |

## 🔒 Security

- **No Shell Injection**: Uses Python's native `shutil`, `zipfile`, `subprocess`
- **Timing-Safe Auth**: Uses `secrets.compare_digest()` for token comparison
- **IP Whitelist**: DNS-based client verification with caching
- **Minimal Privileges**: Systemd service with security hardening
- **No Root in Docker**: Container runs as non-root user

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/certdeliver

# Linting
ruff check src/
```

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<div align="center">


**[⬆ Back to Top](#-certdeliver)**

</div>

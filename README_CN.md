<div align="center">

# 🔐 CertDeliver

**自动化 SSL 证书分发服务**

[![CI](https://github.com/yuanweize/CertDeliver/actions/workflows/ci.yml/badge.svg)](https://github.com/yuanweize/CertDeliver/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL_v3-blue?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-支持-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker/)

**[English](README.md)** · **[中文文档](README_CN.md)**

---

*安全地将 Let's Encrypt 证书自动分发到多台服务器，无需手动干预。*

</div>

## 📖 项目简介

CertDeliver 可以自动将 SSL 证书从中心服务器分发到多台客户端机器。当 certbot 更新证书后，CertDeliver 会自动打包证书并让客户端自动下载。

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Certbot       │────▶│  CertDeliver    │────▶│   客户端 1      │
│   (证书更新)     │     │  服务器         │     │   (nginx/xray)  │
└─────────────────┘     └─────────────────┘     ├─────────────────┤
                                                │   客户端 2      │
                                                │   (nginx/xray)  │
                                                └─────────────────┘
```

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🔐 **安全认证** | 常量时间令牌比较，防止时序攻击 |
| 🌐 **IP 白名单** | 基于 DNS 的客户端验证 |
| 📦 **自动打包** | Certbot 钩子自动打包证书 |
| 🔄 **自动同步** | 客户端自动轮询和更新证书 |
| 🐳 **Docker 支持** | 一键 Docker Compose 部署 |
| ⚡ **现代技术栈** | Python 3.10+、FastAPI、Pydantic、类型提示 |

## 🚀 快速开始

### 系统要求

- Python 3.10 或更高版本
- Certbot（用于证书生成）
- Linux 服务器（Debian/Ubuntu 或 RHEL/CentOS）

### 安装

```bash
# 克隆仓库
git clone https://github.com/yuanweize/CertDeliver.git
cd CertDeliver

# 使用 pip 安装
pip install .

# 或者运行安装脚本
sudo bash scripts/install.sh
```

### Docker 部署

```bash
cd docker
cp ../.env.example .env
# 编辑 .env 配置
docker compose up -d
```

## ⚙️ 配置说明

CertDeliver 使用环境变量进行配置，创建 `.env` 文件：

```bash
# 服务器配置
CERTDELIVER_TOKEN=你的安全随机令牌
CERTDELIVER_DOMAIN_LIST=client1.example.com,client2.example.com
CERTDELIVER_PORT=8000
CERTDELIVER_TARGETS_DIR=/opt/CertDeliver/targets

# 客户端配置
CERTDELIVER_CLIENT_SERVER_URL=https://cert.example.com/api/v1/
CERTDELIVER_CLIENT_TOKEN=你的安全随机令牌
CERTDELIVER_CLIENT_CERT_NAME=cert
CERTDELIVER_CLIENT_CERT_DEST_PATH=/etc/ssl/certs
CERTDELIVER_CLIENT_POST_UPDATE_COMMAND=systemctl reload nginx
```

> 📄 查看 [config/.env.example](config/.env.example) 了解所有可用配置项。

## 📦 服务器部署

### 1. 配置 Certbot

```bash
# 阿里云 DNS 插件示例
certbot certonly \
  -a dns-aliyun \
  --certbot-dns-aliyun:dns-aliyun-credentials /etc/letsencrypt/dns-key \
  -d "*.example.com" \
  --cert-name cert
```

### 2. 设置更新钩子

```bash
# 添加到 crontab
crontab -e

# 添加以下行：
0 0,12 * * * certbot renew -q --post-hook "certdeliver-hook"
```

### 3. 启动服务

```bash
# 方式一：直接运行
certdeliver-server

# 方式二：Systemd 服务
sudo cp CertDeliver.service /etc/systemd/system/
sudo systemctl enable --now certdeliver

# 方式三：Docker
cd docker && docker compose up -d
```

### 4. 反向代理（推荐）

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

## 📱 客户端部署

### 1. 安装

```bash
pip install git+https://github.com/yuanweize/CertDeliver.git
```

### 2. 配置环境变量

```bash
export CERTDELIVER_CLIENT_SERVER_URL="https://cert.example.com/api/v1/"
export CERTDELIVER_CLIENT_TOKEN="你的令牌"
export CERTDELIVER_CLIENT_CERT_NAME="cert"
export CERTDELIVER_CLIENT_CERT_DEST_PATH="/etc/nginx/ssl"
export CERTDELIVER_CLIENT_POST_UPDATE_COMMAND="systemctl reload nginx"
```

### 3. 设置定时任务

```bash
# 每天检查两次更新
crontab -e

# 添加：
30 6,18 * * * certdeliver-client >> /var/log/certdeliver.log 2>&1
```

## 📁 项目结构

```
CertDeliver/
├── src/certdeliver/           # 源代码
│   ├── config.py              # 配置管理 (Pydantic)
│   ├── server/                # FastAPI 服务器
│   │   ├── app.py             # 应用入口
│   │   ├── routes.py          # API 端点
│   │   ├── auth.py            # 认证模块
│   │   └── whitelist.py       # IP 白名单
│   ├── client/                # 证书下载器
│   │   └── downloader.py
│   └── hooks/                 # Certbot 钩子
│       └── certbot_hook.py
├── tests/                     # 单元测试
├── docker/                    # Docker 部署
├── config/                    # 配置示例
├── scripts/                   # 安装脚本
├── pyproject.toml             # 包配置
└── README.md
```

## 🔌 API 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 服务信息和客户端 IP |
| `/health` | GET | 健康检查 |
| `/api/v1/{file}` | GET | 下载/检查证书 |

### 查询参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `token` | string | ✅ | 认证令牌 |
| `download` | bool | ❌ | 强制下载模式 |

## 🔒 安全特性

- **无 Shell 注入**：使用 Python 原生 `shutil`、`zipfile`、`subprocess`
- **时序安全认证**：使用 `secrets.compare_digest()` 比较令牌
- **IP 白名单**：基于 DNS 的客户端验证，带缓存
- **最小权限**：Systemd 服务安全加固
- **非 Root Docker**：容器以非 root 用户运行

## 🧪 开发指南

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 类型检查
mypy src/certdeliver

# 代码检查
ruff check src/
```

## 📄 开源许可

本项目基于 **GNU General Public License v3.0** 开源 - 详见 [LICENSE](LICENSE) 文件。

## 🤝 参与贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

---

<div align="center">

Made with ❤️ by [yuanweize](https://github.com/yuanweize)

**[⬆ 返回顶部](#-certdeliver)**

</div>

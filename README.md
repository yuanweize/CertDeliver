# CertDeliver
证书分发服务 Certificate Deliver Service
# [English](https://github.com/yuanweize/CertDeliver/blob/main/README.md) | [中文](https://github.com/yuanweize/CertDeliver/blob/main/README_CN.md)
## 1. Set certbot
Command for set up certbot 

```
certbot certonly -a dns-aliyun --certbot-dns-aliyun:dns-aliyun-credentials /etc/letsencrypt/YOURDNSKEY -d *.regin.0 -d *.regin.1 --force-renewal --cert-name cert    #Option: --dry-run
```

This cron command updates the certificate by certbot and runs a hook job [cert_hook.py] that compresses the certificate dir `target_dir="cert"`[same as --cert-name] in `input_path = "/etc/letsencrypt/live/"` into a .zip file and move to the target directory `output_path = "/opt/CertDeliver/targets/"`

```
crontab -e
0 0,12 * * * sleep 461 && certbot renew -q --post-hook "/usr/bin/python3 /opt/CertDeliver/cert_hook.py"
```
## 2. Set server
Set LOCAL_TOKEN and DOMAIN_LIST[whitelist] in server.py

It will monitor the /target/ folder which in server.py directory

```
LOCAL_TOKEN ="your_token"
DOMAIN_LIST = ["*.regin.0","*.regin.1"]
```
Daemon run by systemctl
```
wget https://raw.githubusercontent.com/yuanweize/CertDeliver/main/CertDeliver.service
mv CertDeliver.service /etc/systemd/system/CertDeliver.service
systemctl daemon-reload
systemctl enable CertDeliver
systemctl restart CertDeliver
systemctl status CertDeliver
```

## 3. Set client
Set "SERVER_URL, TOKEN, CERT_FILE_NAME, MOVE_PATH" for your client.py

```
SERVER_URL = "https://cert/api/v1/"
TOKEN = "your token"
CERT_FILE_NAME = "cert"  #[same as --cert-name]
MOVE_PATH = "/etc/XrayR/cert" #Your target dir
```

Cron only for client

```
30 6,18 * * * sleep 100 && python3 /opt/CertDeliver/client.py" 
#Run at 06:30 AM and 06:30 PM
```

nginx reverse proxy 
```
location ^~ /
{
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
}

#PROXY-END/
```

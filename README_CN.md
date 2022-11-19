# CertDeliver
证书分发服务 Certificate Deliver Service
## 1.设置certbot
设置certbot的命令
```
certbot certonly -a dns-aliyun --certbot-dns-aliyun:dns-aliyun-credentials /etc/letsencrypt/YOURDNSKEY -d *.regin.0 -d *.regin.1 --force-renewal --cert-name cert #Option: --dry-run
```
这个cron命令通过certbot更新证书，并运行一个钩子工作[cert_hook.py]，将'input_path = "/etc/letsencrypt/live/"'中的证书目录'target_dir="cert"'[与-cert-name相同]压缩成一个.zip文件并移动到目标目录'output_path = "/opt/CertDeliver/targets/"
```
crontab -e
0 0,12 * * * sleep 461 && certbot renew -q --post-hook "/usr/bin/python3 /opt/CertDeliver/cert_hook.py"
```
## 2.设置服务器
在server.py中设置LOCAL_TOKEN和DOMAIN_LIST[白名单]。
它将监视server.py目录下的/target/文件夹
```
LOCAL_TOKEN = "your_token" 。
DOMAIN_LIST = ["*.regin.0", "*.regin.1"] 。
```
通过systemctl运行的守护程序
```
wget https://raw.githubusercontent.com/yuanweize/CertDeliver/main/CertDeliver.service
mv CertDeliver.service /etc/systemd/system/CertDeliver.service
systemctl daemon-reload
systemctl enable CertDeliver
systemctl 重新启动 CertDeliver
systemctl status CertDeliver
```
## 3.设置客户端
为你的客户端.py设置 "SERVER_URL, TOKEN, CERT_FILE_NAME, MOVE_PATH"。
```
server_url = "https://cert/api/v1/"
TOKEN = "你的令牌"
CERT_FILE_NAME = "cert" #[与-cert-name相同]
MOVE_PATH = "/etc/XrayR/cert" #你的目标目录
```
Cron只用于客户端
```
30 6,18 * * * sleep 100 && python3 /opt/CertDeliver/client.py"
#在上午06:30和下午06:30运行
```
nginx反向代理
```
位置 ^~ /
{
proxy_pass http://backend:8000。
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header REMOTE-HOST $remote_addr;
}
#PROXY-END/
```

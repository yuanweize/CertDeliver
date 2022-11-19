# CertDeliver
证书分发服务, Certificate Deliver Service


This cron command updates the certificate by certbot and runs a hook job [cert_hook.py] that compresses the certificates in /etc/letsencrypt/live/ into a .zip file and move to the target directory /opt/CertDeliver/targets/ 
```
crontab -e
0 0,12 * * * sleep 461 && certbot renew -q --post-hook "/usr/bin/python3 /opt/CertDeliver/cert_hook.py"
```

Cron only for client
```
30 6,18 * * * sleep 100 && python3 /opt/CertDeliver/client.py" 
#Run at 06:30 AM and 06:30 PM
```
systemctl status CertDeliver
/etc/systemd/system/CertDeliver.service
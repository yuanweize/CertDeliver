#!/bin/bash
install_path="/opt/CertDeliver"

echo "Certificate Deliver Service"
echo "Project：github.com/yuanweize/CertDeliver"
echo "make sure you have installed python3 and pip3"
echo "==============================================================="
if python3 -V >/dev/null 2>&1; then
    echo "Python3 is installed"
    python_path=$(which python3)
    echo "Python3 path：$python_path"
else
    echo "Python3 does not exist, please install Python3 first"
    if [ -f /etc/debian_version ]; then
        apt update && apt -y install python3 python3-pip
    elif [ -f /etc/redhat-release ]; then
        yum -y install python3 python3-pip
    else
       echo "can't install python3"
       exit;
    fi
fi
if pip3 >/dev/null 2>&1; then
    echo "pip3 ready installed"
else
    echo "pip3 not installed, start install"
    if [ -f /etc/debian_version ]; then
        apt update && apt -y install python3-pip
    elif [ -f /etc/redhat-release ]; then
        yum -y install python3-pip
    else
       echo "Cannot detect the current system, exit"
       exit;
    fi
    echo "pip3 install success"
fi

echo "CertDeliver install path: $install_path"
echo "Please enter API Token"
read -e api_token
echo "Please enter DOMAIN_LIST"
read -e DOMAIN_LIST
echo "Start install CertDeliver……"
mkdir /tmp/install_certdeliver
cd /tmp/install_certdeliver
wget https://raw.githubusercontent.com/yuanweize/CertDeliver/main/main.py -O main.py
wget https://raw.githubusercontent.com/yuanweize/CertDeliver/main/requirements.txt -O requirements.txt
SERVICE_FILE="[Unit]
Description=CertDeliver
After=network.target

[Service]
User=root
WorkingDirectory=$install_path
LimitNOFILE=4096
ExecStart=$python_path $install_path/client.py -t $api_token -d $DOMAIN_LIST
Restart=on-failure
RestartSec=5s
KillMode=mixed

[Install]
WantedBy=multi-user.target"
if [ ! -f "main.py" ];then
    echo "main.py not found"
    exit 1
fi
if [ ! -d "$install_path" ]; then
    mkdir "$install_path"
fi
pip3 install -r requirements.txt
cp main.py "$install_path"/main.py
if [ ! -f "/usr/lib/systemd/system/CertDeliver.service" ];then
    rm -rf /usr/lib/systemd/system/CertDeliver.service
fi
echo -e "${SERVICE_FILE}" > /lib/systemd/system/CertDeliver.service
systemctl daemon-reload
systemctl enable CertDeliver
systemctl restart CertDeliver
systemctl status CertDeliver
echo "Default service name: CertDeliver.service"
echo "Install completed"
exit 0

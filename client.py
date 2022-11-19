import requests
import os
import time
import logging
SERVER_URL = "https://cert/api/v1/"
TOKEN = "your token"
CERT_FILE_NAME = "cert"
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP = str(int(time.time()))
MOVE_PATH = "/etc/XrayR/cert"
TMP_PATH = "/tmp/cert"+TIMESTAMP+"/"

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s-----client:CertDownloader', level=logging.INFO,filename=LOCAL_PATH+'/log')

def move_cert(fname):
    logging.info("move cert")
    if os.path.exists(MOVE_PATH):
        if os.path.exists(MOVE_PATH+"_"+"bak"):
            os.system("rm -rf "+MOVE_PATH+"_"+"bak")
        os.rename(MOVE_PATH,MOVE_PATH+"_"+"bak")
        os.mkdir(MOVE_PATH)
        os.system("unzip "+LOCAL_PATH+"/cert/"+fname+" -d "+TMP_PATH)
        try:
            os.system("mv "+TMP_PATH+"fullchain.pem "+MOVE_PATH+"/fullchain.pem")
            os.system("mv "+TMP_PATH+"privkey.pem "+MOVE_PATH+"/privkey.pem")
        except:
            logging.warning("move cert error")
        logging.info("move cert success")
        os.system("rm -rf "+TMP_PATH)
    restart_xrayr=os.popen("XrayR restart")
    if "成功" in restart_xrayr.read():
        logging.info("restart xrayr success")
    else:
        logging.warning("restart xrayr error")
    restart_xrayr.close()

    
    
def flag_set():
    if not os.path.exists(LOCAL_PATH+"/cert"):
        os.mkdir(LOCAL_PATH+"/cert")
    for root, dirs, files in os.walk(LOCAL_PATH+"/cert"):
        if len(files) == 0:
            logging.info("no local files")
            return True
        elif len(files) == 1:
            logging.info("one local file")
            if files[0].split("_")[0] == CERT_FILE_NAME:
                logging.info("file name match")
                return files[0]

def main():
    IN_UPDATE = False
    logging.info("update cert")
    download_flag = flag_set()
    if download_flag==True:
        logging.info("download cert by first time")
        r = requests.get(SERVER_URL+CERT_FILE_NAME+"_"+TIMESTAMP, params={"token": TOKEN,"download":True})
    elif download_flag==None:
        return logging.info("download_flag is None[file in cert folder are more than one]")
    else:
        logging.info("check update by timestamp")
        IN_UPDATE = True
        r = requests.get(SERVER_URL+download_flag.split(".")[0], params={"token": TOKEN})
    if r.status_code == 200 and "error" not in r.text:
        fname = r.headers["content-disposition"].split(";")[1].split("=")[1].replace('"', '')
        if IN_UPDATE: os.remove(LOCAL_PATH+"/cert/"+download_flag)
        with open(LOCAL_PATH+"/cert/"+fname, "wb") as f:
            f.write(r.content)
            logging.info("download success")
        move_cert(fname)
    else:
        msg="have error or status code not 200: "+str(r.status_code)+":"+r.text
        logging.info(msg)

if __name__ == "__main__":
    main()
    # https://cert/api/v1/cert_16687041030?token=

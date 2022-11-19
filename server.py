from starlette.responses import FileResponse
from fastapi import FastAPI, Request
import uvicorn
import os,logging, socket


LOCAL_TOKEN ="your_token"
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
DOMAIN_LIST = ["www.baidu.com","www.google.com"]#Your domain name managed by certbot
WHITE_LIST = {}

app = FastAPI()
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s-----server:app', level=logging.INFO,filename=LOCAL_PATH+'/log_server',filemode='a')

@app.get("/")
def read_root(request: Request):
    client_host = request.client.host
    return {"CertDELIVER": "Welcome to CertDELIVER", "Your IP is": client_host}

def whitelist_check(client_host):
    def update_whitelist():
        for domain in DOMAIN_LIST:
            try:
                WHITE_LIST[domain] = socket.gethostbyname(domain)
            except Exception as e:
                logging.error(e)
    if len(WHITE_LIST) != len(DOMAIN_LIST):
        logging.info("Update whitelist because of length not match WHITE_LIST_LEN: %s DOMAIN_LIST_LEN: %s" % (len(WHITE_LIST),len(DOMAIN_LIST)))
        update_whitelist()
    if client_host in WHITE_LIST.values():
        return True
    else:
        update_whitelist()
        logging.warning("Update whitelist because of client_host not in WHITE_LIST")
        if client_host in WHITE_LIST.values():
            return True
    
@app.get("/api/v1/{file_name}")
def check_update(file_name: str, token: str, download: bool = False, request: Request = None):
    client_host = request.client.host
    logging.info(f"client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
    if not whitelist_check(client_host):
        logging.info(WHITE_LIST)
        logging.warning(f"client_host:{client_host} is not in whitelist or some domain is not resolve")
        return {"status": "error", "message": "client host is not in whitelist"}
    if token != LOCAL_TOKEN:
        logging.warning("token error client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
        return {"error": "token is not valid"}
    for root, dirs, files in os.walk(LOCAL_PATH+"/targets/"):
        if len(files) != 1:
            return {"error": "too many local files"} 
        local_file=files[0]
        local_filename=local_file.split("_")[0]
        local_timestamp=int(local_file.split("_")[1].split(".")[0])
        try:
            remote_filename=file_name.split("_")[0]
            remote_timestamp=int(file_name.split("_")[1].split(".")[0])
        except:
            logging.warning("remote file name is not illegal client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
            return {"error": "remote file name is not illegal"}
        if download:
            if local_filename == remote_filename:
                logging.info("Client first time download file",local_file)
                return FileResponse(root+local_file, filename=local_file)
            else:
                logging.info("file not found client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
                return {"error": "file not found"}
        if local_filename != remote_filename:
            logging.info("Client need update file but file name not match client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
            return {"error": "file not match"}
        elif local_timestamp == remote_timestamp:
            logging.info("file not changed Client_IP: " + client_host)
            return {"error": "file is not update"}
        elif local_timestamp < remote_timestamp or remote_timestamp<1668704100:
            logging.info("Client need update file but file timestamp not match client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
            return {"error": "remote timestamp is illegal????????Not possible"}
        elif local_timestamp > remote_timestamp:
            logging.info("download file by timestamp check client_host:{client_host} file_name:{file_name} token:{token} download:{download} local_file:{local_file}")
            return FileResponse(root+local_file, filename=local_file)
        else:
            logging.warning("unknown error client_host:{client_host} file_name:{file_name} token:{token} download:{download}")
            return {"error": "unknown error"}
if __name__ == "__main__":
    uvicorn.run(app="server:app", port=8000, host="*", proxy_headers=True, forwarded_allow_ips="*")

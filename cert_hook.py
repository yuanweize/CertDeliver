import logging,os,time,zipfile

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s----cert_hook', level=logging.INFO,filename=LOCAL_PATH+'/log_server',filemode='a')

def zip_cert(input_path,output_path,target_dir):
    logging.info("zip cert run by certbot %s %s %s",input_path,output_path,target_dir)
    timestamp = str(int(time.time()))
    if os.path.exists(output_path):
        os.system("rm -rf "+output_path)
    os.mkdir(output_path)
    output_zipfile = output_path+target_dir+"_"+timestamp+".zip"
    path = os.path.join(input_path, target_dir)
    is_path = os.path.exists(path)
    if is_path:
        zipf = zipfile.ZipFile(output_zipfile, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(path):
            fpath = root.replace(path, '')
            for file in files:
                logging.info("zip file: "+file)
                zipf.write(os.path.join(root, file), os.path.join(fpath, file))
        logging.info("zip file: "+output_zipfile)
        zipf.close()
    else:
        logging.info("Target Dir not found")
if __name__ == "__main__":
    input_path = "/etc/letsencrypt/live/"
    output_path = "/opt/CertDeliver/targets/"
    target_dir="cert"
    zip_cert(input_path,output_path,target_dir)

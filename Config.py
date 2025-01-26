with open('../config', 'r') as f:
    data = f.readlines()
ACCESS_KEY  = data[0].strip()
SECRET_KEY  = data[1].strip()
PASSPHRASE = data[2].strip()
HOST_IP = data[3].strip()
HOST_USER = data[4].strip()
HOST_PASSWD = data[5].strip()
HOST_IP_1 = data[6].strip()

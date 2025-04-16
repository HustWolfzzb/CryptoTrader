from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import paramiko
from pathlib import Path

# 配置
local_dir = "/home/zzb/Quantify/okx"  # 监控目录
remote_hosts = ["node61", "node62"]  # 远程节点
remote_user = "zzb"  # 远程用户名


# 传输文件到远程服务器
def transfer_file(local_path, remote_path, host, remote_user=remote_user):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=remote_user)
        sftp = ssh.open_sftp()

        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.listdir(remote_dir)
        except IOError:  # 如果远程目录不存在，则创建
            sftp.mkdir(remote_dir)

        # 上传文件
        sftp.put(local_path, remote_path)
        print(f"[INFO] {local_path} transferred to {host}:{remote_path}")

        sftp.close()
    except Exception as e:
        print(f"[ERROR] Failed to transfer {local_path} to {host}: {e}")
    finally:
        ssh.close()


# 监控处理程序
class ChangeHandler(FileSystemEventHandler):
    def __init__(self, local_dir, remote_hosts):
        super().__init__()
        self.local_dir = local_dir
        self.remote_hosts = remote_hosts

    def on_modified(self, event):
        self.process_event(event)

    def on_created(self, event):
        self.process_event(event)

    def process_event(self, event):
        # 排除自身代码文件
        if event.is_directory:
            return
        file_path = event.src_path
        if file_path.endswith(( '.py', '.keras', '.txt', '.md')):
            relative_path = os.path.relpath(file_path, self.local_dir)
            for host in self.remote_hosts:
                remote_path = f"/home/zzb/Quantify/okx/{relative_path}"
                transfer_file(file_path, remote_path, host)

        if file_path.endswith(('.py', '.md')):
            relative_path = os.path.relpath(file_path, self.local_dir)
            for host in [HOST_IP, '66.187.4.55']:
                remote_path = f"/root/Quantify/okx/{relative_path}"
                transfer_file(file_path, remote_path, host, HOST_USER)


# 主函数
if __name__ == "__main__":
    event_handler = ChangeHandler(local_dir, remote_hosts)
    observer = Observer()
    observer.schedule(event_handler, local_dir, recursive=True)
    observer.start()
    print(f"[INFO] Monitoring directory: {local_dir}")
    count = 0
    try:
        while True:
            time.sleep(3)  # 每 5 秒检测一次
            count +=3
            if count % 60 == 0:
                os.system('scp root@66.187.4.10:/root/Quantify/okx/chart_for_group/*all_coin* ./chart_for_group/')
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    
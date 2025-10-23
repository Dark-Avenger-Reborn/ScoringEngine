import subprocess
import random
import paramiko
import threading
import requests
import ldap3

class Services:
    def __init__(self):
        self.ip = self.rotate_private_ips()
        self.grading_cycle_count = 0  # Initialize grading cycle counter

    def rotate_private_ips(self):
        self.ip = f"10.0.0.{random.randint(2,254)}"
        subprocess.run(f"ifconfig eth0 {self.ip}", shell=True)

    def increment_grading_cycle(self):
        self.grading_cycle_count += 1  # Increment the grading cycle counter

    def ssh_connection(self, username, password, ip, port=22):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=port, username=username, password=password, timeout=20)

            stdin, stdout, stderr = client.exec_command('ls')
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            client.close()

            if error:
                return (False, error)
            return (True, output)
        except Exception as e:
            return (False, str(e))

    def web_request(self, url):
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                return (True, response.text)
            return (False, response.reason)
        except Exception as e:
            return (False, str(e))

    def ping_host(self, ip):
        try:
            response = subprocess.run(f"ping -c 4 {ip}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=20)
            if response.returncode == 0:
                return (True, response.stdout.decode())
            return (False, response.stderr.decode())
        except Exception as e:
            return (False, str(e))

    def active_directory(self, domain, username, password, timeout):
        try:
            server = ldap3.Server(domain, connect_timeout=timeout)
            conn = ldap3.Connection(server, user=username, password=password)
            if conn.bind():
                conn.unbind()
                return (True, "Authentication successful")
            else:
                return (False, f"Authentication failed: {conn.result}")
        except Exception as e:
            return (False, str(e))
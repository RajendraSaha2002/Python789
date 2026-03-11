import time
import random
import threading
from SELinux_database import insert_audit_log


# Simulates a Linux Kernel generating MAC denial events over time
def generate_fake_avc_logs():
    subjects = ['httpd_t', 'mysqld_t', 'container_t', 'ftpd_t', 'sshd_t']
    objects = ['shadow_t', 'etc_t', 'user_home_t', 'var_log_t', 'httpd_sys_content_t']
    classes = ['file', 'dir', 'tcp_socket', 'process']

    while True:
        time.sleep(random.randint(3, 10))  # Generate a log every 3 to 10 seconds

        subj = random.choice(subjects)
        obj = random.choice(objects)
        tclass = random.choice(classes)
        action = 'denied' if random.random() > 0.2 else 'granted'

        scontext = f"system_u:system_r:{subj}:s0"
        tcontext = f"system_u:object_r:{obj}:s0"
        details = f"{'prevented' if action == 'denied' else 'allowed'} {tclass} access"

        insert_audit_log(action, scontext, tcontext, tclass, details)
        print(f"KERNEL [SELinux]: type=AVC msg=audit(): {action} for context={subj}")


def start_simulation():
    thread = threading.Thread(target=generate_fake_avc_logs, daemon=True)
    thread.start()
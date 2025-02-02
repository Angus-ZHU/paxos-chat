import argparse
import subprocess
import time
from multiprocessing import Process
from config import ServerClusterConfig

parser = argparse.ArgumentParser(description='Script mode to run the cluster')
parser.add_argument('-f', default=2, type=int, help='number of tolerating failures')
parser.add_argument('-c', default='config.json', type=str, help='the config filename')
parser.add_argument('-skip_slots', default=None, type=str, help='skip slots in the form of 1,2,3,4')
parser.add_argument('-client_n', default=3, type=int, help='number of clients')
parser.add_argument('-loss', default=0.0, type=float, help='the message loss ratio')
parser.add_argument('-timeout', default=0.5, type=float, help='the message timeout setting')


def generate_config_file(config, f, loss, timeout):
    script = ["python", "generate_test_config.py"]
    script.extend(["-c", str(config)])
    script.extend(["-f", str(f)])
    script.extend(["-loss", str(loss)])
    script.extend(["-timeout", str(timeout)])
    subprocess.call(" ".join(script), shell=True)


def run_client(config):
    script = ["python", "client.py"]
    script.extend(["-c", str(config)])
    subprocess.call(" ".join(script), shell=True)


def run_server(config, uid, skip_slots=None):
    script = ["python", "server.py"]
    script.extend(["-c", str(config)])
    script.extend(["-uid", str(uid)])
    if skip_slots is not None:
        script.extend(["-skip_slots", str(skip_slots)])
    subprocess.call(" ".join(script), shell=True)


if __name__ == '__main__':
    args = parser.parse_args()
    generate_config_file(args.c, args.f, args.loss, args.timeout)
    config = ServerClusterConfig.read_config(args.c)
    for i in range(2 * args.f + 1):
        if i == 0:
            # initial master can see the skip slots
            p = Process(target=run_server, args=(args.c, i, args.skip_slots))
        else:
            p = Process(target=run_server, args=(args.c, i))
        p.start()
    time.sleep(1)
    for i in range(args.client_n):
        p = Process(target=run_client, args=(args.c,))
        p.start()

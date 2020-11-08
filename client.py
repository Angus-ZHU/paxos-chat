import argparse
import sys
import time
import random
import secrets
import jsonpickle
from multiprocessing import Process
import socket
from message import *
from config import ServerClusterConfig

MAX_PACKAGE_LENGTH = 4096


class Client(object):

    def __init__(self, config: ServerClusterConfig, timeout=1.0, message_loss=0.0):
        self.message_loss = message_loss
        self.timeout = timeout
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", 0))
        self.addresses = config.get_all_replica_ip_port()

    def _send(self, address, byte: bytes):
        if random.uniform(0, 1) < self.message_loss:
            # message loss
            return
        self.socket.sendto(byte, address)

    def send_all(self, message: BaseMessage):
        msg = str(message).encode("utf-8")
        for address in self.addresses:
            self._send(address, msg)

    def _receive(self) -> ClientReply:
        message = None
        while message is None:
            # print(self.socket.getsockname())
            raw, address = self.socket.recvfrom(MAX_PACKAGE_LENGTH)
            message = jsonpickle.decode(raw.decode("utf-8"))
        assert isinstance(message, ClientReply)
        return message

    def worker(self):
        uid = secrets.token_hex(16)
        body = secrets.token_urlsafe(16)
        print("requesting message: {uid: %s, message: %s}" % (uid, body))
        operation = Operation(uid, body)
        request = ClientRequest(operation)
        self.send_all(request)
        reply = self._receive()
        # print(reply)
        if operation == reply.operation:
            if reply.success:
                print("message send success")
            else:
                print("message send failed")
        else:
            sys.stderr.write("Error: Client receiving random reply")

    def main(self):
        while True:
            p = Process(target=self.worker)
            p.start()
            p.join(self.timeout)
            if p.is_alive():
                p.terminate()
                print("message send timeout")


parser = argparse.ArgumentParser(description='Start a new client')
parser.add_argument('-c', default='config.json', type=str, help='the config filename')
parser.add_argument('-loss', default=0.0, type=float, help='random percentage to loss message')
parser.add_argument('-timeout', default=5, type=float, help='timeout in seconds')


if __name__ == '__main__':
    args = parser.parse_args()
    config = ServerClusterConfig.read_config(args.c)
    client = Client(config, args.timeout, args.loss)
    client.main()





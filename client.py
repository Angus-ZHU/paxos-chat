import time
from multiprocessing import Process
import threading

# import socket
#
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind()
# sock.recv()
# sock.send()


class Client(object):

    def __init__(self, replicas, p=0):
        self.p = p
        self.lock = threading.Lock()
        self.view = 0
        self.replicas = replicas

    def run(self):
        sockets = list()
        for replica in self.replicas:

    def receive(self, s):



#
#
# def send_request():
#     pass
#
#
# def _receive_message_implementation():
#     valid = False
#     from_id = None
#     return from_id
#
#
# def _receive_message_worker(threshold=0):
#     received_id = []
#     while len(received_id) < threshold:
#         from_id = _receive_message_implementation()
#         if from_id is not None and from_id not in received_id:
#             received_id.append(from_id)
#
#
# def receive_message(threshold=0, timeout=100):
#     t = Process(target=_receive_message_worker, args=(threshold,))
#
#     t.start()
#     t.join(timeout)
#     if t.is_alive():
#         t.terminate()
#         # timeout happened
#         return False
#     else:
#         # success
#         return True


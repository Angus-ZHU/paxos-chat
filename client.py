import time
from multiprocessing import Process
import threading
import socket
import util
from server import ChatMessage

# import socket
#
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind()
# sock.recv()
# sock.send()

class Client(object):

    def __init__(self, replicas_address: list[tuple], msg_list: list, p=0.0):
        self.p = p
        self.replicas_address = replicas_address
        self.msg_list = msg_list
        self.uid = 0
        self.lock = threading.Lock()
        self.last_send_time = 0

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Send the first message to each node
            self.send_to_all(s)
            self.last_send_time = time.time()
            t_timeout_resend = threading.Thread(target=self.time_out_resend, args = (s, ))
            t_timeout_resend.daemon = True
            t_timeout_resend.start()
            t_receive = threading.Thread(target=self.receive, args = (s, ))
            t_receive.start()
            t_receive.join()

    def receive(self, s):
        while True:
            msg, master_address = util.msg_receive(s)
            if not msg:
                continue

            # Deserialize the message
            chat_message = ChatMessage.deserilize(msg)

            # If it's not an ack message or the uid not equal to current uid, ignore it
            if chat_message.type is not ACK or chat_message.uid != self.uid:
                continue

            self.lock.acquire()

            self.uid += 1
            if self.uid >= len(self.msg_list):
                break

            util.msg_send(s, master_address, self.msg_list[self.uid])
            self.last_send_time = time.time()

            self.lock.release()

    # Client has to send to all replicas since master could die
    def send_to_all(self, s):
        for replica_address in self.replicas_address:
            util.msg_send(s, replica_address, self.msg_list[self.uid])

    def time_out_resend(self, s):
        while True:
            self.lock.acquire()

            if time.time() - self.last_send_time < 10:
                continue
            self.send_to_all(s)

            self.lock.release()
            time.sleep(2)









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


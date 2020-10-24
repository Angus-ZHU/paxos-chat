import json
import socket
import random
import threading
import time


def msg_send(socket, address, msg, p = 0.0):
    """
    The function for message sending via socket

    :param socket: The socket used to send message
    :param address: The tuple of ip and port (ip, port)
    :param msg: The msg is going to send
    :param p: The loss probability
    :return: None
    """
    if p > 0 and random.uniform(0, 1) < p:
        return

    encode_msg = msg.encode('utf-8')
    socket.sendto(encode_msg, address)



def msg_receive(socket):
    """
    Receive a message corresponding to a socket.

    :param socket: the socket some client/server bind with
    :return: the message received
    """

    # Receive the header first, get the message length
    packet, address = socket.recvfrom(4096)
    if not packet:
        return None, None
    msg = packet.decode("utf-8")

    return msg, address



# sample usage
def server():
    HOST = ''                 # Symbolic name meaning all available interfaces
    PORT = 50007              # Arbitrary non-privileged port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        msg, address = msg_receive(s)
        print('Received from client', repr(address))
        if not msg:
            return
        msg_send(s, address, repr(msg))

def client():
    HOST = ''  # The remote host
    PORT = 50007  # The same port as used by the server
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        msg_send(s, (HOST, PORT), 'Hello, world')
        msg, address = msg_receive(s)
        print('Received from server', repr(msg))


t1 = threading.Thread(target = server)
t1.daemon = True
t1.start()
t2 = threading.Thread(target = client)
t2.daemon = True
t2.start()

time.sleep(3)
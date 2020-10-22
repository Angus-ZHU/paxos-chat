import json
import socket
import random
import threading
import time

# The int byte length, which is the length of message
INT_LEN = 4


def msg_send(socket, msg, p = 0.0):
    """
    The function for message sending via socket

    :param socket: The socket used to send message
    :param msg: The msg is going to send
    :param p: The loss probability
    :return: None
    """
    if p > 0 and random.uniform(0, 1) < p:
        return

    encode_len = len(msg).to_bytes(4, 'big')
    encode_msg = msg.encode('utf-8')
    socket.sendall(encode_len + encode_msg)



def msg_receive(socket):
    """
    Receive a message corresponding to a socket.

    :param socket: the socket some client/server bind with
    :return: the message received
    """

    # Receive the header first, get the message length
    msg_length = bytearray()
    while len(msg_length) < INT_LEN:
        packet = socket.recv(INT_LEN - len(msg_length))
        if not packet:
            return None
        msg_length.extend(packet)

    msg_length = int.from_bytes(msg_length, 'big')
    print(msg_length)

    # Receive the raw message
    msg = bytearray()
    while len(msg) < msg_length:
        packet = socket.recv(msg_length - len(msg))
        if not packet:
            return None
        msg.extend(packet)

    msg = msg.decode("utf-8")

    return msg



# sample usage
def server():
    HOST = ''                 # Symbolic name meaning all available interfaces
    PORT = 50007              # Arbitrary non-privileged port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            data = msg_receive(conn)
            print('Received', repr(data))

def client():
    HOST = ''  # The remote host
    PORT = 50007  # The same port as used by the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        msg_send(s, 'Hello, world')
        data = s.recv(1024)


t1 = threading.Thread(target = server)
t1.daemon = True
t1.start()
t2 = threading.Thread(target = client)
t2.daemon = True
t2.start()

time.sleep(0.5)
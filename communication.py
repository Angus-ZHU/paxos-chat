import socket
import jsonpickle
import random
from multiprocessing import Process, Queue
from functools import wraps
from typing import Type
from config import ServerClusterConfig
from message import Proposal, HeartBeat, BaseMessage, ClientRequest, ClientReply, Accept, IAmLeader, YouAreLeader, \
    InitMessage, ReplicaReady
from error import DeadMasterError, NoReplyError, FollowNewMasterError, NewMasterError

MAX_PACKAGE_LENGTH = 4096


class CommunicationLayer(object):
    def __init__(self, uid, master_uid, config: ServerClusterConfig, view_modulo=0, heartbeat_timeout=None):
        self.uid = uid
        self.master_uid = master_uid
        if heartbeat_timeout is not None:
            self.heartbeat_timeout = heartbeat_timeout
        else:
            # do not use a separate timeout
            self.heartbeat_timeout = config.timeout
        self.view_modulo = view_modulo
        self.master_address = config.get_address(master_uid)
        self.master_heartbeat_address = config.get_heartbeat_address(master_uid)
        self.message_loss = config.get_message_loss(uid)
        self._bind_port(uid, config)
        self.addresses = config.get_all_replica_ip_port(uid)
        # [(message, address), ]
        self.message_buffer = []

    def _bind_port(self, uid, config: ServerClusterConfig):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.timeout = config.timeout
        self.set_timeout(self.timeout)
        self.socket.bind(config.get_address(uid))

    def clear_buffer(self):
        self.message_buffer = []
        self.socket.setblocking(False)
        try:
            while True:
                self.socket.recv(MAX_PACKAGE_LENGTH)
        except socket:
            pass
        self.socket.setblocking(True)

    def check_master_alive(self):
        # if itself is the master
        if self.uid == self.master_uid:
            return True
        # use a new socket for timeout check
        original_socket = self.socket
        original_buffer = self.message_buffer
        # a new separate socket for heartbeat check
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.message_buffer = []
        self.socket.settimeout(self.heartbeat_timeout)
        self.send_heart_beat_request_to_master()
        while True:
            try:
                heartbeat, message = self.get_heartbeat()
                if heartbeat.uid == self.master_uid:
                    self.socket = original_socket
                    original_buffer.extend(self.message_buffer)
                    self.message_buffer = original_buffer
                    return True
            except socket.timeout:
                self.socket = original_socket
                self.message_buffer = original_buffer

    def disable_timeout(self):
        self.set_timeout(None)

    def set_timeout(self, timeout):
        self.timeout = timeout
        self.socket.settimeout(timeout)

    def _get_message(self, t: Type[BaseMessage]):
        for i in range(len(self.message_buffer)):
            message, address = self.message_buffer[i]
            if isinstance(message, t):
                self.message_buffer.pop(i)
                return message, address
        # if not in buffer
        while True:
            try:
                message, address = self._receive()
            except socket.timeout:
                self._handle_timeout()
                # _handle_timeout will always raise exception, so the return here means nothing
                return
            if isinstance(message, t):
                return message, address
            else:
                # heartbeat responses are not stored
                # init messages are also not stored
                if not isinstance(message, (HeartBeat, InitMessage)):
                    self.message_buffer.append((message, address))

    def get_replica_ready(self):
        return self._get_message(ReplicaReady)

    def get_heartbeat(self):
        return self._get_message(HeartBeat)

    def get_init_message(self):
        return self._get_message(InitMessage)

    def get_client_request(self):
        return self._get_message(ClientRequest)

    def get_client_reply(self):
        return self._get_message(ClientReply)

    def get_proposal(self):
        return self._get_message(Proposal)

    def get_accept(self):
        return self._get_message(Accept)

    def get_follower(self):
        return self._get_message(YouAreLeader)

    def get_anything(self):
        return self._get_message(YouAreLeader)

    def reply_heart_beat(self, address):
        raise NotImplemented

    def send_heart_beat_request_to_master(self, repeat=3):
        request = HeartBeat(self.uid, need_reply=True)
        # create a temp socket for heart beat check
        for _ in range(repeat):
            self.send_one(self.master_heartbeat_address, request)

    def _handle_timeout(self):
        # itself is the master case is handled inside check_master_alive()
        if self.check_master_alive():
            raise NoReplyError
        else:
            raise DeadMasterError

    def _handle_special_messages(self, message, address):
        if isinstance(message, HeartBeat):
            if message.need_reply:
                # should be handled by HeartbeatResponder
                raise KeyError
                # self.reply_heart_beat(address)
            else:
                return message
        elif isinstance(message, IAmLeader):
            # the master it self will not answer to IAmLeader message
            # but with new leader elected, it will response to the new leader InitMessage
            if self.master_uid == self.uid:
                return None
            if message.view_modulo > self.view_modulo or (
                    message.view_modulo == self.view_modulo and message.uid > self.master_uid):
                if self.check_master_alive():
                    return None
                else:
                    raise FollowNewMasterError(message.uid, message.view_modulo, False)
            else:
                # got a message from lower leader
                return None
        elif isinstance(message, InitMessage):
            if message.uid == self.master_uid:
                return message
            else:
                raise NewMasterError(message.uid, message.view_modulo, message.accepted)
        else:
            return message

    def _receive(self):
        message = None
        while message is None:
            raw, address = self.socket.recvfrom(MAX_PACKAGE_LENGTH)
            message = jsonpickle.decode(raw.decode("utf-8"))
            message = self._handle_special_messages(message, address)
        return message, address

    def _send(self, address, byte: bytes):
        if random.uniform(0, 1) < self.message_loss:
            # message loss
            return
        self.socket.sendto(byte, address)

    def send_one(self, address, message: BaseMessage):
        self._send(address, str(message).encode("utf-8"))

    def send_all(self, message: BaseMessage):
        msg = str(message).encode("utf-8")
        for address in self.addresses:
            self._send(address, msg)


class HeartbeatResponder(CommunicationLayer):
    def __init__(self, uid, master_uid, config: ServerClusterConfig, view_modulo=0):
        # only master will need a heartbeat responder
        assert uid == master_uid
        super(HeartbeatResponder, self).__init__(uid, master_uid, config, view_modulo)

    def _bind_port(self, uid, config: ServerClusterConfig):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.disable_timeout()
        self.socket.bind(config.get_heartbeat_address(uid))

    def reply_heart_beat(self, address):
        reply = HeartBeat(self.uid, need_reply=False)
        return self.send_one(address, reply)

    def _handle_special_messages(self, message, address):
        if isinstance(message, HeartBeat):
            if message.need_reply:
                self.reply_heart_beat(address)
        return None

    def run(self):
        p = Process(target=self._receive)
        p.start()


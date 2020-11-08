import argparse
import random
import socket
from functools import wraps
from config import ServerClusterConfig
from multiprocessing import Pool, Queue, Process, Manager
from message import *
from server_state import ServerState

MAX_PACKAGE_LENGTH = 4096


def propose_worker_wrapper(func):
    def timeout_wrap(self, proposal: Proposal):
        p = Process(target=func, args=(self, proposal))
        p.daemon = True
        p.start()
        p.join(self.get_default_timeout())
        if p.is_alive():
            p.terminate()
            self.result_queue.put((proposal.slot, False))

    @wraps(func)
    def outer_wrap(self, proposal: Proposal):
        p = Process(target=timeout_wrap, args=(self, proposal))
        p.start()
        # start the worker and move on

    return outer_wrap


class Server(object):
    def __init__(self, uid, config: ServerClusterConfig, view_modulo=0, skip_slots=None):
        self.uid = uid
        self.config = config
        self.view_modulo = view_modulo

        self.state = ServerState(self.uid, skip_slots=skip_slots)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(config.get_address(uid))

        self.manager = Manager()
        self.message_queues = {}
        self.result_queue = self.manager.Queue()

    def get_f(self):
        return self.config.f

    def get_default_timeout(self):
        return self.config.timeout

    def get_master_address(self):
        return self.config.get_address(self.state.master_uid)

    def get_message_loss(self):
        return self.config.get_message_loss(self.uid)

    def get_addresses(self):
        return self.config.get_all_replica_ip_port(self_uid=self.uid)

    def _send(self, address, byte: bytes):
        if random.uniform(0, 1) < self.get_message_loss():
            # message loss
            return
        self.socket.sendto(byte, address)

    def send_one(self, address, message: BaseMessage):
        self._send(address, str(message).encode("utf-8"))

    def send_all(self, message: BaseMessage):
        msg = str(message).encode("utf-8")
        for address in self.get_addresses():
            self._send(address, msg)

    def _receive(self):
        message = None
        while message is None:
            raw, address = self.socket.recvfrom(MAX_PACKAGE_LENGTH)
            message = jsonpickle.decode(raw.decode("utf-8"))
        return message, address

    def dispatcher(self):
        if self.state.is_master:
            self.master_dispatcher()
        else:
            self.replica_dispatcher()

    @propose_worker_wrapper
    def propose_worker(self, proposal: Proposal):
        self.send_all(proposal)
        message_queue = self.message_queues[proposal.slot]
        accepted_uid = []
        while len(accepted_uid) < self.get_f():
            new_uid = message_queue.get()
            if new_uid not in accepted_uid:
                accepted_uid.append(new_uid)
        delivered_messages = self.state.learn_operation(proposal.slot, proposal.operation)
        if delivered_messages is not None:
            for i in delivered_messages:
                self.result_queue.put((i, True))

    def reply_client_worker(self):
        while True:
            delivered_slot, success = self.result_queue.get()
            operation = self.state.get_learned_operation(delivered_slot)
            reply = ClientReply(success, operation)
            self.send_one(operation.client_address, reply)

    def handle_accept(self, accept: Accept):
        if accept.proposal.slot in self.message_queues:
            queue = self.message_queues[accept.proposal.slot]
            queue.put(accept.uid)

    def reply_heartbeat(self, address):
        heartbeat = HeartBeat(self.uid, need_reply=False)
        self.send_one(address, heartbeat)

    def handle_client_request(self, message: ClientRequest):
        slot = self.state.propose_operation(message.operation)
        proposal = Proposal(self.uid, slot, message.operation)
        # create new queue
        new_queue = self.manager.Queue()
        self.message_queues[slot] = new_queue
        self.propose_worker(proposal)

    def master_dispatcher(self):
        while True:
            message, address = self._receive()
            if isinstance(message, ClientRequest):
                # print("get client request")
                message.operation.client_address = address
                self.handle_client_request(message)
            elif isinstance(message, Accept):
                self.handle_accept(message)
            elif isinstance(message, IAmLeader):
                # todo:
                pass
            elif isinstance(message, InitMessage):
                # todo:
                pass
            elif isinstance(message, HeartBeat):
                if message.need_reply:
                    self.reply_heartbeat(address)
            # ignore all other messages

    def master_main(self):
        p = Process(target=self.reply_client_worker)
        p.start()
        self.master_dispatcher()

    def handle_proposal(self, proposal: Proposal):
        if self.state.master_uid == proposal.master_uid:
            if self.state.can_accept_operation(proposal.slot):
                self.state.accept_operation(proposal.slot, proposal.operation)
                accept_message = Accept(self.uid, proposal)
                self.send_one(self.get_master_address(), accept_message)

    def replica_dispatcher(self):
        while True:
            message, address = self._receive()
            if isinstance(message, Proposal):
                self.handle_proposal(message)
            elif isinstance(message, InitMessage):
                # todo
                pass

    def replica_main(self):
        self.replica_dispatcher()

    def main(self):
        if self.state.is_master:
            print("master")
            self.master_main()
        else:
            print("replica")
            self.replica_main()


parser = argparse.ArgumentParser(description='Start a new client')
parser.add_argument('-c', default='config.json', type=str, help='the config filename')
parser.add_argument('-uid', default=1, type=int, help='server id')
parser.add_argument('-skip_slots', default=None, type=str, help='skip slots in the form of 1,2,3,4')

if __name__ == '__main__':
    args = parser.parse_args()
    # either this is the original master or the skip_slots is None
    assert args.uid == 0 or args.skip_slots is None
    config = ServerClusterConfig.read_config(args.c)
    server = Server(args.uid, config, skip_slots=args.skip_slots)
    server.main()

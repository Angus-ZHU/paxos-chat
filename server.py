import argparse
import random
import socket
from functools import wraps
from typing import Type
from config import ServerClusterConfig
from multiprocessing import Queue, Process, Manager
from message import *
from error import *
from server_state import ServerState

MAX_PACKAGE_LENGTH = 4096


def follow_new_master_wrapper(func):
    @wraps(func)
    def wrap(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except FollowNewMasterError as e:
            self.follow_new_master(e.master_uid, e.view_modulo)
        except DeadMasterError:
            self.promote_to_master()

    return wrap


def propose_worker_wrapper(func):
    def timeout_wrap(self, proposal: Proposal):
        p = Process(target=func, args=(self, proposal))
        p.daemon = True
        p.start()
        p.join(self.get_default_timeout())
        if p.is_alive():
            p.terminate()
            self.message_queues[proposal.slot].close()
            self.result_queue.put((proposal, False))

    @wraps(func)
    def outer_wrap(self, proposal: Proposal):
        p = Process(target=timeout_wrap, args=(self, proposal))
        p.start()
        # start the worker and move on

    return outer_wrap


class Server(object):
    def __init__(self, uid, config: ServerClusterConfig, skip_slots=None):
        self.uid = uid
        self.config = config

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

    def get_addresses(self):
        return self.config.get_all_replica_ip_port(self_uid=self.uid)

    def _send(self, address, byte: bytes):
        if not self.state.is_master and random.uniform(0, 1) < self.config.message_loss:
            # message loss
            return
        self.socket.sendto(byte, address)

    def send_one(self, address, message: BaseMessage):
        self._send(address, str(message).encode("utf-8"))

    def send_all(self, message: BaseMessage):
        msg = str(message).encode("utf-8")
        for address in self.get_addresses():
            self._send(address, msg)

    def _receive_from_socket(self):
        raw, address = self.socket.recvfrom(MAX_PACKAGE_LENGTH)
        message = jsonpickle.decode(raw.decode("utf-8"))
        return message, address

    def receive(self):
        return self._receive_from_socket()

    def _receive_with_timeout(self, expecting: Type[BaseMessage] = None):
        self.socket.settimeout(self.get_default_timeout())
        try:
            while True:
                message, address = self._receive_from_socket()
                if expecting is None or isinstance(message, expecting):
                    return message, address
                else:
                    pass
        except Exception as e:
            raise e
        finally:
            self.socket.settimeout(None)

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
        message_queue.close()
        delivered_proposals = self.state.learn_proposal(proposal)
        for proposal in delivered_proposals:
            self.result_queue.put((proposal, True))

    def reply_client_worker(self):
        while True:
            proposal, success = self.result_queue.get()
            reply = ClientReply(success, proposal.operation)
            self.send_one(proposal.client_address, reply)

    def handle_accept(self, accept: Accept):
        if accept.proposal.slot not in self.message_queues:
            new_queue = Queue()
            self.message_queues[accept.proposal.slot] = new_queue
        queue = self.message_queues[accept.proposal.slot]
        try:
            queue.put(accept.uid)
        except:
            pass

    def reply_heartbeat(self, address):
        heartbeat = HeartBeat(self.uid, need_reply=False)
        self.send_one(address, heartbeat)

    def handle_client_request(self, message: ClientRequest, client_address):
        proposal = self.state.propose_operation(message.operation, client_address)
        # create new queue
        if proposal.slot not in self.message_queues:
            new_queue = Queue()
            self.message_queues[proposal.slot] = new_queue
        self.propose_worker(proposal)

    def master_dispatcher(self):
        while True:
            message, address = self.receive()
            if isinstance(message, ClientRequest):
                # print("get client request")
                self.handle_client_request(message, address)
            elif isinstance(message, Accept):
                if message.proposal.master_uid == self.uid:
                    self.handle_accept(message)
            elif isinstance(message, HeartBeat):
                if message.need_reply:
                    self.reply_heartbeat(address)
            # ignore all other messages

    def master_main(self):
        p = Process(target=self.reply_client_worker)
        p.start()
        self.master_dispatcher()

    def replica_learner(self, proposal: Proposal):
        message_queue = self.message_queues[proposal.slot]
        accepted_uid = []
        # with the proposal and self, it only need f-1 other accept messages
        while len(accepted_uid) < self.get_f() - 1:
            new_uid = message_queue.get()
            if new_uid not in accepted_uid:
                accepted_uid.append(new_uid)
        message_queue.close()
        self.state.learn_proposal(proposal)

    def handle_proposal(self, proposal: Proposal):
        if self.state.master_uid == proposal.master_uid:
            if self.state.accept_proposal(proposal):
                accept_message = Accept(self.uid, proposal)
                self.send_all(accept_message)
                if proposal.slot not in self.message_queues:
                    self.message_queues[proposal.slot] = Queue()
                p = Process(target=self.replica_learner, args=(proposal,))
                p.start()

    def check_master_alive(self, retry=3):
        if self.uid == self.state.master_uid:
            # check master alive is only called by replica, this is cause by failed promotion
            # should be considered the same as the master is dead
            return False
        # because of message loss, need multiple heartbeat
        for _ in range(retry):
            heartbeat = HeartBeat(self.uid, need_reply=True)
            self.send_one(self.get_master_address(), heartbeat)
        try:
            self._receive_with_timeout(HeartBeat)
        except socket.timeout:
            return False
        return True

    def can_follow_new_leader(self, new_master_uid, new_master_view_modulo):
        return new_master_uid > self.state.master_uid or new_master_view_modulo > self.state.view_modulo

    def propose_any_learned_operations(self):
        all_learned_proposals = self.state.get_all_learned_proposals()
        # fill in no-ops
        slot = 0
        while len(all_learned_proposals):
            if slot in all_learned_proposals:
                all_learned_proposals.pop(slot)
            else:
                # no_ops
                proposal = Proposal(self.uid, self.state.view_modulo, None, slot, Operation())
                self.state.learn_proposal(proposal)
            slot += 1
        all_learned_proposals = self.state.get_all_learned_proposals()
        # print("here, ", all_learned_proposals)
        for proposal in all_learned_proposals.values():
            self.send_all(proposal)

    def promote_to_master(self):
        if self.uid < self.state.master_uid:
            self.state.update_master_state(self.uid, self.state.view_modulo + 1)
        else:
            self.state.update_master_state(self.uid)
        leader_message = IAmLeader(self.uid, self.state.view_modulo)
        self.send_all(leader_message)
        learned_message = {}
        follow_uid = []
        while len(follow_uid) < self.get_f():
            try:
                while True:
                    message, _ = self._receive_with_timeout()
                    if isinstance(message, YouAreLeader):
                        break
                    elif isinstance(message, IAmLeader):
                        if self.can_follow_new_leader(message.uid, message.view_modulo):
                            self.follow_new_master(message.uid, message.view_modulo)
            except socket.timeout:
                print("promote to master failed")
                self.state.is_master = False
                self.main()
                exit()
            if message.follower_uid not in follow_uid:
                print("get a follower ", message.follower_uid)
                # json do not allow int key
                new_learned = {}
                for slot in message.learned:
                    new_learned[int(slot)] = message.learned[slot]
                follow_uid.append(message.follower_uid)
                learned_message.update(new_learned)
        # become master
        self.state.update_new_state(learned_message)
        self.main()
        return

    def follow_new_master(self, master_uid, view_modulo):
        print("current master %s, view %s." % (self.state.master_uid, self.state.view_modulo),
              " following new master %s, view %s" % (master_uid, view_modulo))
        print()
        self.state.update_master_state(master_uid, view_modulo)
        learned_proposals = self.state.get_all_learned_proposals()
        you_are_leader = YouAreLeader(self.uid, learned_proposals)
        self.send_one(self.config.get_address(master_uid), you_are_leader)
        # time.sleep(self.get_default_timeout())
        self.main()

    def replica_dispatcher(self):
        while True:
            try:
                message, address = self._receive_with_timeout()
            except socket.timeout:
                if self.check_master_alive():
                    continue
                else:
                    raise DeadMasterError()
            if isinstance(message, Proposal):
                self.handle_proposal(message)
            if isinstance(message, Accept):
                self.handle_accept(message)
            if isinstance(message, IAmLeader):
                if self.can_follow_new_leader(message.uid, message.view_modulo):
                    raise FollowNewMasterError(message.uid, message.view_modulo)

    def replica_main(self):
        self.replica_dispatcher()

    @follow_new_master_wrapper
    def main(self):
        if self.state.is_master:
            print("master")
            self.propose_any_learned_operations()
            self.master_main()
        else:
            print("replica")
            print("current master %s, view %s " % (self.state.master_uid, self.state.view_modulo))
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
    if args.skip_slots is not None:
        args.skip_slots = args.skip_slots.split(',')
        args.skip_slots = [int(slot) for slot in args.skip_slots]
    server = Server(args.uid, config, skip_slots=args.skip_slots)
    server.main()

import sys
import hashlib
import jsonpickle
from typing import List, Dict
from functools import wraps
from config import ServerConfig, ServerClusterConfig
from message import Operation, Proposal, ClientReply, ClientRequest, Accept, InitMessage, IAmLeader, YouAreLeader, \
    ReplicaReady
from communication import CommunicationLayer
from error import DeadMasterError, NoReplyError, FollowNewMasterError, NewMasterError





def follow_new_master_wrapper(func):
    @wraps(func)
    def wrap(self: Server, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except FollowNewMasterError as e:
            self.follow_new_master(e.master_uid, e.view_modulo)
        except NewMasterError as e:
            self.init_new_master(e.master_uid, e.view_modulo, e.accepted)
        except DeadMasterError:
            self.promote_to_master()

    return wrap


class Server(object):
    def __init__(self, uid, cluster_config: ServerClusterConfig):
        self.uid = uid
        self.f = cluster_config.f
        self.config = cluster_config
        self.state = ServerState(self.uid)
        self.communicator = CommunicationLayer(self.uid, self.state.master_uid, cluster_config)

    def update_new_master(self, master_uid, view_modulo):
        self.state.master_uid = master_uid
        self.state.modulo = view_modulo
        self.state.update_master_state()

    def disable_timeout(self):
        self.communicator.disable_timeout()

    def set_default_timeout(self):
        self.communicator.set_timeout(self.config.timeout)

    def reply_to_client(self, client_address, operation: Operation, success=True):
        message = ClientReply(success, operation)
        self.communicator.send_one(client_address, message)

    def wait_for_matching_accept(self, proposal: Proposal, threshold):
        accept_uids = set()
        while len(accept_uids) < threshold:
            accept, address = self.communicator.get_accept()
            if accept.proposal == proposal:
                accept_uids.add(accept.uid)

    def propose(self, proposal: Proposal):
        self.communicator.send_all(proposal)
        try:
            self.wait_for_matching_accept(proposal=proposal, threshold=self.f)
        except NoReplyError:
            return False
        return True

    def master_wait_for_replica(self):
        init_message = InitMessage(self.uid, self.state.modulo, self.state.get_all_learned_operations())
        followers = []
        while len(followers) < self.f + 1:
            self.communicator.send_all(message=init_message)
            try:
                while True:
                    ready_message = self.communicator.get_replica_ready()
                    followers.append(ready_message.replica_uid)
            except NoReplyError:
                pass

    def master_main(self):
        while True:
            # will wait indefinitely for a client request
            self.disable_timeout()
            request, address = self.communicator.get_client_request()
            self.set_default_timeout()
            operation = request.operation
            # should be unnecessary, but just to be safe and with limited overhead
            self.state.execute()
            proposal = Proposal(slot=len(self.state.delivered_operations), operation=operation)
            if self.propose(proposal=proposal):
                self.state.accept_message(proposal.slot, proposal.operation)
                self.reply_to_client(address, operation, success=True)
            else:
                self.reply_to_client(address, operation, success=False)

    def reply_accept(self, proposal: Proposal):
        reply = Accept(self.uid, proposal)
        self.communicator.send_all(reply)

    def replica_wait_for_init(self):
        self.disable_timeout()
        init_message = self.communicator.get_init_message()
        self.set_default_timeout()
        self.state.update_new_state(init_message.accepted)
        ready_message = ReplicaReady(self.uid)
        self.communicator.send_one(self.config.get_address(self.state.master_uid), ready_message)
        return init_message

    def replica_main(self):
        while True:
            proposal, address = self.communicator.get_proposal()
            if self.state.can_accept_operation(proposal.slot):
                self.reply_accept(proposal)
                try:
                    self.wait_for_matching_accept(proposal, self.f)
                except NoReplyError:
                    # not enough reply with in timeout, but master still alive
                    continue
                self.state.accept_message(proposal.slot, proposal.operation)
            else:
                sys.stderr.write('Error: get proposal with conflicting slot')

    @follow_new_master_wrapper
    def promote_to_master(self):
        # todo
        pass

    @ follow_new_master_wrapper
    def init_new_master(self, master_uid, view_modulo, accepted: Dict[int, Operation]):
        self.update_new_master(master_uid, view_modulo)
        self.state.update_new_state(accepted)
        self.replica_main()

    @follow_new_master_wrapper
    def follow_new_master(self, master_uid, view_modulo):
        self.update_new_master(master_uid, view_modulo)
        accepted_messages = self.state.get_all_learned_operations()
        follow_message = YouAreLeader(self.uid, accepted_messages)
        self.communicator.send_one(self.config.get_address(master_uid), follow_message)
        self.replica_wait_for_init()
        self.replica_main()

    @follow_new_master_wrapper
    def main(self):
        if self.state.is_master:
            self.master_wait_for_replica()
            self.master_main()
        else:
            self.replica_wait_for_init()
            self.replica_main()


if __name__ == '__main__':
    pass

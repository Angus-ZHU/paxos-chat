import jsonpickle
from typing import List, Dict


class BaseMessage(object):
    def __str__(self):
        return jsonpickle.encode(self)

    def __repr__(self):
        return self.__str__()


class ReplicaReady(BaseMessage):
    def __init__(self, replica_uid):
        self.replica_uid = replica_uid


class HeartBeat(BaseMessage):
    def __init__(self, uid, need_reply):
        self.uid = uid
        self.need_reply = need_reply


class Operation(BaseMessage):
    def __init__(self, uid=None, message=None, client_address=None):
        self.uid = uid
        self.message = message
        self.client_address = client_address

    def if_nop(self):
        return self.uid is None

    def __eq__(self, other):
        return type(self) == type(other) and \
               self.uid == other.uid and \
               self.message == other.message


class ClientRequest(BaseMessage):
    def __init__(self, operation: Operation):
        self.operation = operation


class ClientReply(BaseMessage):
    def __init__(self, success, operation: Operation):
        self.operation = operation
        self.success = success


class Proposal(BaseMessage):
    def __init__(self, master_uid, slot, operation: Operation):
        self.master_uid = master_uid
        self.slot = slot
        self.operation = operation

    def __eq__(self, other):
        return type(self) == type(other) and \
               self.operation == other.operation


class Accept(BaseMessage):
    def __init__(self, uid, proposal: Proposal):
        self.uid = uid
        self.proposal = proposal


class IAmLeader(BaseMessage):
    def __init__(self, uid, view_modulo):
        self.uid = uid
        self.view_modulo = view_modulo


class YouAreLeader(BaseMessage):
    def __init__(self, follower_uid, learned: Dict[int, Operation]):
        self.follower_uid = follower_uid
        self.learned = learned


class InitMessage(BaseMessage):
    def __init__(self, uid, view_modulo, accepted: Dict[int, Operation]):
        self.uid = uid
        self.view_modulo = view_modulo
        self.accepted = accepted


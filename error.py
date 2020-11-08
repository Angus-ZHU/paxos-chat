from message import Operation
from typing import List, Dict


class DeadMasterError(Exception):
    pass


class NoReplyError(Exception):
    pass


class FollowNewMasterError(Exception):
    # a new master sends I am leader message trying to promote
    def __init__(self, master_uid, view_modulo):
        self.master_uid = master_uid
        self.view_modulo = view_modulo
        super(FollowNewMasterError, self).__init__()


class NewMasterError(Exception):
    # a new master has been selected and send to init message
    def __init__(self, master_uid, view_modulo, accepted: Dict[int, Operation]):
        self.master_uid = master_uid
        self.view_modulo = view_modulo
        self.accepted = accepted
        super(NewMasterError, self).__init__()

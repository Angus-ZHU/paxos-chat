class DeadMasterError(Exception):
    pass


class FollowNewMasterError(Exception):
    # a new master sends I am leader message trying to promote
    def __init__(self, master_uid, view_modulo):
        self.master_uid = master_uid
        self.view_modulo = view_modulo
        super(FollowNewMasterError, self).__init__()

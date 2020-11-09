import sys
import jsonpickle
import hashlib
from multiprocessing import Manager

from functools import wraps
from message import Operation, Proposal
from typing import Dict


def write_show_state(func):
    @wraps(func)
    def wrap(self, *args, **kwargs):
        # todo write state
        result = func(self, *args, **kwargs)
        # self.write_state()
        self.digest_state()
        return result

    return wrap


class ServerState(object):
    def __init__(self, uid, master_uid=0, skip_slots=None):
        self.view_modulo = 0
        self.uid = uid

        self.master_uid = master_uid
        self.is_master = False
        self.update_master_state()

        self.manager = Manager()
        self.lock = self.manager.Lock()
        self.lock_count = 0
        # {slot: Operation}
        self.delivered_operations = self.manager.dict()
        self.learned_operation_buffer = self.manager.dict()
        self.accepted_operation_buffer = self.manager.dict()
        # !!!! skip_slots is only used by master
        # !!!! should lost after view change
        assert self.is_master or skip_slots is None
        if skip_slots is None:
            self.skip_slots = []
        else:
            self.skip_slots = skip_slots

    def acquire_lock(self):
        if self.lock_count == 0:
            self.lock.acquire()
        self.lock_count += 1

    def release_lock(self):
        self.lock_count -= 1
        if self.lock_count == 0:
            self.lock.release()

    def update_master_state(self, master_uid=None, new_modulo=None):
        if master_uid is not None:
            self.master_uid = master_uid
        if new_modulo is not None:
            self.view_modulo = new_modulo
        if self.uid == self.master_uid:
            self.is_master = True
        else:
            self.is_master = False

    @write_show_state
    def update_new_state(self, learned: Dict[int, Operation]):
        self.acquire_lock()
        self.accepted_operation_buffer.clear()
        self.learned_operation_buffer.clear()
        self.learned_operation_buffer.update(learned)
        result = self.execute()
        self.release_lock()
        return result

    def get_all_learned_operations(self) -> Dict[int, Operation]:
        self.acquire_lock()
        result = {}
        result.update(self.delivered_operations.copy())
        result.update(self.learned_operation_buffer.copy())
        self.release_lock()
        return result

    def execute(self):
        result = []
        self.acquire_lock()
        k = -1
        while True:
            k += 1
            if k in self.skip_slots:
                continue
            if k in self.delivered_operations:
                continue
            if k in self.learned_operation_buffer:
                operation = self.learned_operation_buffer.pop(k)
                self.delivered_operations[k] = operation
                proposal = Proposal(self.uid, k, operation)
                result.append(proposal)
            else:
                break
        self.release_lock()
        return result

    def can_accept_operation(self, slot):
        self.acquire_lock()
        can = slot not in self.delivered_operations and \
              slot not in self.learned_operation_buffer and \
              slot not in self.accepted_operation_buffer and \
              slot not in self.skip_slots
        self.release_lock()
        return can

    def propose_operation(self, operation: Operation):
        self.acquire_lock()
        slot = self.get_next_available_slot()
        self.accepted_operation_buffer[slot] = operation
        self.release_lock()
        return slot

    def accept_operation(self, slot, operation: Operation):
        self.acquire_lock()
        if self.can_accept_operation(slot):
            self.accepted_operation_buffer[slot] = operation
        else:
            sys.stderr.write('Fatal: accepting operation with conflicting slot')
        self.release_lock()

    @write_show_state
    def learn_operation(self, slot, operation: Operation):
        self.acquire_lock()
        self.accepted_operation_buffer.pop(slot, 'None')
        self.learned_operation_buffer[slot] = operation
        result = self.execute()
        self.release_lock()
        return result
        # if slot in self.accepted_operation_buffer and self.accepted_operation_buffer[slot] == operation:
        #     self.acquire_lock()
        #     self.accepted_operation_buffer.pop(slot, 'None')
        #     self.learned_operation_buffer[slot] = operation
        #     result = self.execute()
        #     self.release_lock()
        #     return result
        # else:
        #     sys.stderr.write('Fatal: can not learn a not accepted operation\n')

    def get_next_available_slot(self):
        i = 0
        while True:
            if self.can_accept_operation(i):
                break
            i += 1
        return i

    # def write_state(self):
    #     filename = 'state_%s.json' % self.uid
    #     with open(filename, 'w') as f:
    #         f.write(jsonpickle.encode(self))

    def digest_state(self):
        print("Server-%s: Sanity Check: %s" % (self.uid, self.get_all_learned_operations()))

        # print('Hash Sanity Check-%s: %s' % (
        #     self.uid, hashlib.sha1(
        #           jsonpickle.encode(self.get_all_learned_operations()).encode()
        #     ).hexdigest()
        # ))

    # @classmethod
    # def restore_state(cls, uid):
    #     filename = 'state_%s.json' % uid
    #     return jsonpickle.decode(open(filename).read())

import sys
import jsonpickle
import hashlib
from multiprocessing import Manager

from functools import wraps
from message import Operation
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

    def update_master_state(self, master_uid=None):
        if master_uid is not None:
            self.master_uid = master_uid
        if self.uid == self.master_uid:
            self.is_master = True
        else:
            self.is_master = False

    def get_learned_operation(self, i):
        if i in self.delivered_operations:
            return self.delivered_operations[i]
        elif i in self.learned_operation_buffer:
            return self.learned_operation_buffer[i]
        else:
            return None

    @write_show_state
    def update_new_state(self, accepted: Dict[int, Operation]):
        self.lock.acquire()
        self.accepted_operation_buffer.clear()
        self.learned_operation_buffer.clear()
        self.learned_operation_buffer.update(accepted)
        result = self.execute(lock_acquired=True)
        self.lock.release()
        return result

    def get_all_accepted_operations(self) -> Dict[int, Operation]:
        result = self.delivered_operations.copy()
        result.update(self.learned_operation_buffer.copy())
        result.update(self.accepted_operation_buffer.copy())
        return result

    def execute(self, lock_acquired=False):
        result = []
        if not lock_acquired:
            self.lock.acquire()
        k = -1
        while True:
            k += 1
            if k in self.skip_slots:
                continue
            if k in self.delivered_operations:
                continue
            if k in self.learned_operation_buffer:
                self.delivered_operations[k] = self.learned_operation_buffer.pop(k)
                result.append(k)
            else:
                break

        if not lock_acquired:
            self.lock.release()
        return result

    def can_accept_operation(self, slot):
        return slot not in self.delivered_operations and \
               slot not in self.learned_operation_buffer and \
               slot not in self.accepted_operation_buffer and \
               slot not in self.skip_slots

    def propose_operation(self, operation: Operation):
        self.lock.acquire()
        slot = self.get_next_available_slot()
        self.accepted_operation_buffer[slot] = operation
        self.lock.release()
        return slot

    @write_show_state
    def accept_operation(self, slot, operation: Operation):
        self.lock.acquire()
        if self.can_accept_operation(slot):
            self.accepted_operation_buffer[slot] = operation
        else:
            sys.stderr.write('Fatal: accepting operation with conflicting slot')
        self.lock.release()

    @write_show_state
    def learn_operation(self, slot, operation: Operation):
        # only called by proposer
        if slot in self.accepted_operation_buffer and self.accepted_operation_buffer[slot] == operation:
            self.lock.acquire()
            self.accepted_operation_buffer.pop(slot, 'None')
            self.learned_operation_buffer[slot] = operation
            result = self.execute(lock_acquired=True)
            self.lock.release()
            return result
        else:
            sys.stderr.write('Fatal: can not learn a not accepted operation\n')

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
        # print("Sanity Check: %s" % self.get_all_accepted_operations())

        print('Hash Sanity Check-%s: %s' % (
            self.uid, hashlib.sha1(
                  jsonpickle.encode(self.get_all_accepted_operations()).encode()
            ).hexdigest()
        ))

    # @classmethod
    # def restore_state(cls, uid):
    #     filename = 'state_%s.json' % uid
    #     return jsonpickle.decode(open(filename).read())

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
        # {slot: Proposal}
        self.delivered_proposals = self.manager.dict()
        self.learned_proposal_buffer = self.manager.dict()
        self.accepted_proposal_buffer = self.manager.dict()
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
    def update_new_state(self, learned: Dict[int, Proposal]):
        self.acquire_lock()
        self.accepted_proposal_buffer.clear()
        self.learned_proposal_buffer.clear()
        self.learned_proposal_buffer.update(learned)
        result = self.execute()
        self.release_lock()
        return result

    def get_all_learned_proposals(self) -> Dict[int, Proposal]:
        self.acquire_lock()
        result = {}
        result.update(self.delivered_proposals.copy())
        result.update(self.learned_proposal_buffer.copy())
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
            if k in self.delivered_proposals:
                continue
            if k in self.learned_proposal_buffer:
                proposal = self.learned_proposal_buffer.pop(k)
                self.delivered_proposals[k] = proposal
                result.append(proposal)
            else:
                break
        self.release_lock()
        return result

    def is_empty_slot(self, slot):
        self.acquire_lock()
        empty_slot = slot not in self.delivered_proposals and \
                     slot not in self.learned_proposal_buffer and \
                     slot not in self.accepted_proposal_buffer and \
                     slot not in self.skip_slots
        self.release_lock()
        return empty_slot

    def _can_accept_proposal(self, proposal: Proposal):
        can_accept = False
        if self.is_empty_slot(proposal.slot):
            can_accept = True
        else:
            self.acquire_lock()
            if proposal.slot in self.accepted_proposal_buffer:
                if self.accepted_proposal_buffer[proposal.slot].can_be_replaced_by(proposal):
                    can_accept = True
            self.release_lock()
        return can_accept

    def propose_operation(self, operation: Operation, client_address):
        self.acquire_lock()
        slot = self.get_next_available_slot()
        proposal = Proposal(self.uid, self.view_modulo, client_address, slot, operation)
        self.accepted_proposal_buffer[slot] = proposal
        self.release_lock()
        return proposal

    def accept_proposal(self, proposal: Proposal):
        self.acquire_lock()
        if self._can_accept_proposal(proposal):
            self.accepted_proposal_buffer[proposal.slot] = proposal
            accepted = True
        else:
            accepted = False
        self.release_lock()
        return accepted

    @write_show_state
    def learn_proposal(self, proposal: Proposal):
        self.acquire_lock()
        self.accepted_proposal_buffer.pop(proposal.slot, 'None')
        self.learned_proposal_buffer[proposal.slot] = proposal
        result = self.execute()
        self.release_lock()
        return result

    def get_next_available_slot(self):
        i = 0
        while True:
            if self.is_empty_slot(i):
                break
            i += 1
        return i

    # def write_state(self):
    #     filename = 'state_%s.json' % self.uid
    #     with open(filename, 'w') as f:
    #         f.write(jsonpickle.encode(self))

    def digest_state(self):
        print("Server-%s: Sanity Check: %s" % (self.uid, self.get_all_learned_proposals()))

        # print('Hash Sanity Check-%s: %s' % (
        #     self.uid, hashlib.sha1(
        #           jsonpickle.encode(self.get_all_learned_operations()).encode()
        #     ).hexdigest()
        # ))

    # @classmethod
    # def restore_state(cls, uid):
    #     filename = 'state_%s.json' % uid
    #     return jsonpickle.decode(open(filename).read())

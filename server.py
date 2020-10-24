import sys
import hashlib
import jsonpickle
from config import ServerConfig, ServerClusterConfig


class ChatMessage(object):
    # TODO serializable, deserializable, messageType(ACK, CHAT, PRINT lOG, HEARTBEAT etc)
    def __init__(self, uid=None, message=None):
        self.uid = uid
        self.message = message

    def if_nop(self):
        return self.uid is None


class Proposal(object):
    def __init__(self, slot, message: ChatMessage):
        self.slot = slot
        self.message = message


class ServerState(object):
    def __init__(self, uid, skip_slots=None):
        self.modulo = 0
        self.uid = uid
        self.messages = {}
        if skip_slots is None:
            self.skip_slots = []
        else:
            self.skip_slots = skip_slots
        for slot in self.skip_slots:
            self.messages[slot] = ChatMessage()

        # in case slot 0 is in skip_slots
        self.slot_pointer = -1
        self.increment_slot_pointer()
        self.write_state()
        self.digest_message()

    def increment_slot_pointer(self):
        self.slot_pointer += 1
        while self.slot_pointer in self.skip_slots:
            self.slot_pointer += 1

    def can_accept_message(self, slot):
        # skip slots are occupied with None in __init__
        return slot not in self.messages

    def accept_message(self, slot, message: ChatMessage):
        if self.can_accept_message(slot):
            self.messages[slot] = message
        else:
            sys.stderr.write('Fatal: accepting message with conflicting slot')
        # Persistent
        self.write_state()
        # Sanity Check
        self.digest_message()

    def write_state(self):
        filename = 'state_%s.json' % self.uid
        with open(filename, 'w') as f:
            f.write(jsonpickle.encode(self))

    def digest_message(self):
        print('Hash Sanity Check: %s' %
                  hashlib.sha1(
                      jsonpickle.encode(self.messages).encode()
                  ).hexdigest()
              )

    @classmethod
    def restore_state(cls, uid):
        filename = 'state_%s.json' % uid
        return jsonpickle.decode(open(filename).read())


class Server(object):
    def __init__(self, uid, cluster_config: ServerClusterConfig):
        self.uid = uid
        self.config = cluster_config
        self.master_uid = 0
        self.is_master = False
        self.state = ServerState(self.uid)

        if self.uid == 0:
            self.master = True

    @staticmethod
    def is_replicate_ping(message):
        return False

    def reply_replicate_ping(self, message):
        # todo
        pass

    def receive_from_client(self):
        while True:
            # todo: block until we have a message from client
            message = ChatMessage()
            # replicate ping are replied and
            if self.is_replicate_ping(message):
                self.reply_replicate_ping(message)
            else:
                return message

    def reply_to_client(self, success=True):
        # todo:
        if success:
            pass
        else:
            pass

    def propose_value(self, message):
        # todo
        # propose to replica, wait for f replies
        pass

    def master_main(self):
        message = self.receive_from_client()
        if self.propose_value(message=message):
            self.reply_to_client(success=True)
        else:
            self.reply_to_client(success=False)

    def promote_to_master(self):
        # todo
        pass

    def ping_master(self):
        master_address = self.config.get_master_address()
        # todo ping master
        pass
        ping_success = True
        if ping_success:
            return
        else:
            self.promote_to_master()

    def receive_proposal(self):
        # todo receive proposal from master
        proposal = Proposal(0, ChatMessage())
        return proposal

    def replica_main(self):


    def main(self):
        if self.is_master:
            self.master_main()
        else:
            self.replica_main()



if __name__ == '__main__':
    pass
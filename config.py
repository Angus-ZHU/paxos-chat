import jsonpickle
from typing import List


class ServerConfig(object):
    def __init__(self, uid, ip, port, message_loss=0):
        self.uid = uid
        self.ip = ip
        self.port = port
        self.message_loss = message_loss


class ServerClusterConfig(object):
    def __init__(self, f,
                 master_ip, master_port, heartbeat_ip, heartbeat_port,
                 servers_config: List[ServerConfig],
                 skip_slots=None, timeout=500):
        self.f = f
        self.master_ip = master_ip
        self.master_port = master_port
        self.heartbeat_ip = heartbeat_ip
        self.heartbeat_port = heartbeat_port
        self.timeout = timeout
        if skip_slots is None:
            self.skip_slots = []
        else:
            self.skip_slots = skip_slots
        self.servers_config = servers_config
        assert self.f * 2 + 1 == len(servers_config)

    def write_config(self, config_file='config.json'):
        with open(config_file, 'w') as f:
            f.write(jsonpickle.encode(self))

    def __index__(self, i):
        return self.servers_config[i]

    def get_heartbeat_address(self):
        return self.heartbeat_ip, self.heartbeat_port

    def get_master_address(self):
        return self.master_ip, self.master_port

    def get_all_replica_ip_port(self, self_uid=None):
        result = []
        for config in self.servers_config:
            if self_uid != config.uid:
                # exclude itself when self_uid is set
                result.append((config.ip, config.port))
        return result

    @classmethod
    def read_config(cls, config_file='config.json'):
        return jsonpickle.decode(open(config_file).read())

    @classmethod
    def generate_test_config(cls, f, config_file='config.json'):
        ip = 'localhost'
        servers_config = []
        for i in range(2 * f + 1):
            c = ServerConfig(uid=i, ip=ip, port=i + 23333)
            servers_config.append(c)
        cluster_config = ServerClusterConfig(f=f, master_ip=ip, master_port=23330, heartbeat_ip=ip, heartbeat_port=23331,
                                             servers_config=servers_config)
        cluster_config.write_config(config_file)

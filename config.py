import jsonpickle
from typing import List


class ServerConfig(object):
    def __init__(self, uid, ip, port):
        self.uid = uid
        self.ip = ip
        self.port = port


class ServerClusterConfig(object):
    def __init__(self, f,
                 servers_config: List[ServerConfig],
                 timeout=0.5, message_loss=0):
        self.f = f
        self.message_loss = message_loss
        # timeout in seconds
        self.timeout = timeout
        self.servers_config = servers_config
        assert self.f * 2 + 1 == len(servers_config)

    def write_config(self, config_file='config.json'):
        with open(config_file, 'w') as f:
            f.write(jsonpickle.encode(self))

    def __index__(self, i):
        return self.servers_config[i]

    def get_address(self, uid):
        config = self.servers_config[uid]
        return config.ip, config.port

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
    def generate_test_config(cls, f, config_file='config.json', timeout=0.5, message_loss=0):
        ip = 'localhost'
        servers_config = []
        for i in range(2 * f + 1):
            c = ServerConfig(uid=i, ip=ip, port=i + 23333)
            servers_config.append(c)
        cluster_config = ServerClusterConfig(f=f, servers_config=servers_config,
                                             timeout=timeout, message_loss=message_loss)
        cluster_config.write_config(config_file)

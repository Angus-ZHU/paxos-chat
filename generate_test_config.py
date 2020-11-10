import argparse
from config import ServerClusterConfig, ServerConfig

parser = argparse.ArgumentParser(description='Generate a test config file of that tolerates f failure')
parser.add_argument('-f', default=1, type=int, help='the number of tolerating failures')
parser.add_argument('-c', default='config.json', type=str, help='the config filename')
parser.add_argument('-loss', default=0.0, type=float, help='the message loss ratio')
parser.add_argument('-timeout', default=0.5, type=float, help='the message timeout setting')

if __name__ == '__main__':
    args = parser.parse_args()
    ServerClusterConfig.generate_test_config(args.f, args.c, message_loss=args.loss, timeout=args.timeout)
    config = ServerClusterConfig.read_config(args.c)
    # print(config.get_all_replica_ip_port())
    pass

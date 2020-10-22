import argparse
import jsonpickle
from config import ServerClusterConfig, ServerConfig

parser = argparse.ArgumentParser(description='Generate a test config file of that tolerates f failure')
parser.add_argument('-f', default=10, type=int, help='number of tolerating failures')
parser.add_argument('-c', default='config.json', type=str, help='the config filename')

if __name__ == '__main__':
    args = parser.parse_args()
    ServerClusterConfig.generate_test_config(args.f, args.c)
    config = ServerClusterConfig.read_config(args.c)
    pass

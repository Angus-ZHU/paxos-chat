import signal
import time
from multiprocessing import Process, Queue
from threading import Thread
import gevent

import requests


class MyClass(object):
    def __init__(self):
        self.a = 1



class Layer(object):
    results = Queue()

    def put(self):
        self.results.put(MyClass())
        print("put")

    def get(self):
        print("getting")
        a = self.results.get()
        print(type(a))

    def print_all(self):
        print("all the messages")
        while not self.results.empty():
            print(self.results.get())
        print("end")

    def main(self):
        put = Process(target=self.put)
        get = Process(target=self.get)
        put.start()
        get.start()


def wait():
    time.sleep(1)
    return 2333


class NoResponse(Exception):
    pass

if __name__ == '__main__':
    # l = Layer()
    # l.main()
    p = Process(target=wait)
    p.daemon = True
    p.start()
    p.join(3)
    print("finished")




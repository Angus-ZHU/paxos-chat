import multiprocessing
import time


def func1(d):
    while d['message'] != 'kill':
        print(d['message'])
    print('done')


def func2(d):
    for i in range(60):
        time.sleep(1)
        d['message'] = 'Message ' + str(i)
    d['message'] = 'kill'


if __name__ == '__main__':
    manager = multiprocessing.Manager()
    q = manager.Queue()
    q.put((233, False))
    n, b = q.get()
    print(n, b)


    d = manager.dict()
    l = manager.list([22323])
    d[33] = 32
    d[22] = 22
    d.update({33: 343, 333: 777})
    print(d.get(23, "not exits"))
    print(len(d))
    print(d.pop(333, "666"))
    print(len(d))
    print(33 in d)
    for k, v in d.items():
        print(k, v)
    d.clear()
    # l.clear()
    l.append(32323)
    print(type(d))
    print(type(dict(d)))
    print(dict(d))
    print(type(l))
    print(type(list(l)))
    print(list(l))

    # d['message'] = 'Waiting...'
    # print(d['message'])
    # proc1 = multiprocessing.Process(target=func1, args=(d,))
    # proc2 = multiprocessing.Process(target=func2,args=(d,))
    # proc1.start()
    # for i in range(60):
    #     time.sleep(1)
    #     d['message'] = 'Message ' + str(i)
    # proc2.start()
    # proc1.join()
    # proc2.join()

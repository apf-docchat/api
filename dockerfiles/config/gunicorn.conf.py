import multiprocessing

workers = multiprocessing.cpu_count() + 1
threads = multiprocessing.cpu_count() * 2 + 1

worker_class = 'gevent'

bind = '0.0.0.0:8000'

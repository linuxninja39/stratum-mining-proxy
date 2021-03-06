#!/usr/bin/env python2

import socket
import json
import time

HOST = '127.0.0.1'                 # Symbolic name meaning all available interfaces
PORT = 50013              # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # Enable keepalive packets
s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 60) # Seconds before sending keepalive probes
s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1) # Interval in seconds between keepalive probes
s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 5) # Failed keepalive probles before declaring other end dead
# ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# ss.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # Enable keepalive packets
# ss.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 60) # Seconds before sending keepalive probes
# ss.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1) # Interval in seconds between keepalive probes
# ss.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 5) # Failed keepalive probles before declaring other end dead
remote_pool = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
remote_pool.connect(('stratum.bitcoin.cz', 3333))
s.bind((HOST, PORT))
s.listen(10)
# ss.bind((HOST, 50015))
# ss.listen(10)
# print s.accept()
conn, addr = s.accept()
# sconn, saddr = ss.accept()
start = time.time()
switched = False
print 'Connected by', addr
while 1:
    s_data = {"params": ['127.0.0.1', 50014], "id" : "switch", "method":"mining.proxy_switch"}

    # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s.connect(('127.0.0.1', 50015))
    # s.send(bytes(json.dumps(data)))
    data = conn.recv(4096)
    # ssdata = sconn.recv(4096)
    # if ssdata:
    #     try:
    #         ret = json.loads(data)
    #         print ret
    #         print ret['method']
    #         print ret['params']
    #         if 'method' in ret and 'params' in ret:
    #             # print 'method:', ret['method']
    #             if ret['method'] == 'proxy.switch':
    #             #     print 'params:', ret['params']
    #                 proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #                 proxy.connect(('127.0.0.1', 3333))
    #                 proxy.send(data)
    #                 proxy.close()
    #         print "Received from proxy:", ret
    #     except Exception:
    #         print "Something went wrong"
    if data:
        # if not switched:
        print "Received from proxy:", data
        remote_pool.send(data)
    b_data = remote_pool.recv(4096)
    if b_data:
        # if (time.time() - start) > 10 and not switched:
        #     print 'Switch to new pool'
        #     conn.send(bytes(json.dumps(s_data)))
        #     switched = True
        # # else:
        #     # if not switched:
        print "Received from pool:", b_data
        conn.send(b_data)

#if not data: break
    #conn.sendall(data)
remote_pool.close()
conn.close()
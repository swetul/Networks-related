#!/usr/bin/python
import socket
import sys
import select
import time

print("Beginning Client Node")
localPort = 15046
outPort = 16046

peerNodes = []
clients = []

local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
local.setblocking(False)
local.bind(('127.0.0.1', localPort))
local.listen(socket.SOMAXCONN)
print("Client socket ready!")
time.sleep(3)
while True:
    returnSock, returnAddr = local.accept()
    while True:
        data = returnSock.recv(1024)
        if not data:
            break
        print("Incoming: " + data)
        returnSock.sendall(b'received\r\n')

    returnSock.close()

print("ends")

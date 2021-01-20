#!/usr/bin/python

#   Swetul Patel        
#   Server Node for a distributed chat system
#
import socket
import sys
import select
import time
import json

from zeroconf import IPVersion, ServiceInfo, Zeroconf, ServiceBrowser

# global time variables
clockTime = time.time()
prevTime = time.time()

# port num 15046, 16046
print("Beginning Node.... CTRL-C to exit")
localPort = 15046
outPort = 16046

# server socket for Node connections
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setblocking(False)
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
server.bind((hostname, outPort))
print("Server socket ready!")

# local Socket for client connections
local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
local.setblocking(False)
local.bind(('127.0.0.1', localPort))
local.listen(socket.SOMAXCONN)
print("Client socket ready!")

# lists for select
inputs = [local, server]
outputs = []

# announce presence
desc = {}
myQueue = []
zeroconf = Zeroconf()
unique = hostname

uniqueServ = "Swetul P Node in " + (hostname.split(".")[0])
info = ServiceInfo("_p2pchat._udp.local.",
                   uniqueServ+"._p2pchat._udp.local.", addresses=[socket.inet_aton(ip_address)], port=outPort, properties=desc, server=hostname+"SwetulP.local.")
zeroconf.register_service(info)

# listener class for zeroconf to hear services


class myListener:
    def __init__(self):
        self.chatNodes = {}
        self.infoTable = {}

# new service detected
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        self.infoTable[name] = info
        if type == "_p2pchat._udp.local.":
            nm = uniqueServ+"._p2pchat._udp.local."
            if not (name == uniqueServ+"._p2pchat._udp.local."):
                addre = socket.inet_ntoa(info.addresses[0])
                por = int(info.port)
                neKey = addre + ";" + str(por)
                timd = {"time": int(time.time()),
                        "addresses": addre, "port": por}
                if neKey not in self.chatNodes:
                    self.chatNodes[neKey] = timd
                    print("New node connected: " + name)

    def update_service(self):
        pass

# remove service method when a ping is not received in 2 minutes
    def remove_service(self, zeroconf, type, name):
        if name in self.infoTable:
            info = self.infoTable[name]
            addre = socket.inet_ntoa(info.addresses[0])
            por = int(info.port)
            neKey = addre + ";" + str(por)
            if neKey in self.chatNodes:
                self.chatNodes.pop(neKey)
            print("Node: " + (name.split("._p2pchat._udp.local.")
                              [0]) + " disconnected!")


listener = myListener()
print("Broadcasting Service!")
browser = ServiceBrowser(zeroconf, "_p2pchat._udp.local.", listener)
print("Listening for services")

# ------------------------------------------------------------------------------
# method to send a ping


def sendPing():
    pingMsg = {"command": "PING"}
    pingMsg = json.dumps(pingMsg)
    for node in list(listener.chatNodes):
        ads = listener.chatNodes[node]['addresses']
        sers = int(listener.chatNodes[node]['port'])
        server.sendto(str.encode(pingMsg), (ads, sers))


# ------------------------------------------------------------------------------
# method to update last ping, if a ping is received
def pingReceived(nodeAddr):
    print("Ping received from " + nodeAddr)
    for node in list(listener.chatNodes):
        if node == nodeAddr:
            listener.chatNodes[node]["time"] = int(time.time())

# ------------------------------------------------------------------------------
# check nodes to see if any of them haven't sent a ping in 2 minutes


def checkPingStatus():
    currTime = int(time.time())
    for node in list(listener.chatNodes):
        if currTime > listener.chatNodes[node]["time"] + 115:
            listener.chatNodes.pop(node)
# ------------------------------------------------------------------------------
# close all sockets upon exit of server


def exit_server():
    # clossing all connections to the sockets and zeroConf
    print("Closing all connections and Service")
    server.close()
    local.close()
    for socks in outputs:
        socks.close()
    zeroconf.unregister_service(info)
    zeroconf.close()

# ------------------------------------------------------------------------------
# function that does all the reading and writing messages to and from nodes and other clients


def waitForConnections():
    clockTime = time.time()
    prevTime = time.time()

    try:
        while inputs:
            readable, writable, exceptional = select.select(
                inputs, outputs, inputs, 1)
            # common case no input received skip to bottom
            if len(readable) != 0:

                clientMSG = ""
                serverMsg = ""
                # reading all sockets that have data received
                for readS in readable:
                    # if message is from new client
                    if readS is local:
                        connection, client_address = readS.accept()
                        connection.setblocking(False)
                        inputs.append(connection)
                        outputs.append(connection)
                    # ---------------------------------------------------------
                    # if message is from any node
                    elif readS is server:
                        nodeData, nodeAddr = readS.recvfrom(1024)
                        nodemsg = bytes.decode(nodeData)
                        try:
                            nodemsg = json.loads(nodemsg)
                            if nodemsg['command'] == "PING":
                                pingReceived(
                                    nodeAddr[0] + ";" + str(nodeAddr[1]))

                            elif nodemsg['command'] == "MSG":
                                temp = {}
                                temp["ip"] = nodeAddr[0]
                                temp["port"] = nodeAddr[1]
                                temp["message"] = (
                                    nodemsg['user'], nodemsg['message'])
                                myQueue.append(temp)
                        except Exception:
                            print("Bad message received! from " +
                                  nodeAddr[0]+";"+str(nodeAddr[1]))
                    # message from existing client, just read
                    # ---------------------------------------------------------
                    else:
                        data = readS.recv(1024)

                        if data:
                            data = data.decode("UTF-8").strip()
                            if data == "close" or data == "Close":
                                inputs.remove(readS)
                                outputs.remove(readS)
                                readS.close()
                            else:
                                tempo = data.split(' ', 1)
                                if len(tempo) == 1:
                                    tempo.append("\t")
                                temp = {}
                                temp["ip"] = "0"
                                temp["port"] = 0
                                temp["message"] = (tempo[0], tempo[1])
                                myQueue.append(temp)
                                if readS not in outputs:
                                    outputs.append(s)

                # process all the information received from the clients and the servers that was
                # added to a list(myQueue)
                while len(myQueue) != 0:
                    myDict = myQueue.pop(0)
                    myComp = myDict["ip"] + ";" + str(myDict["port"])
                    sendMessage = myDict["message"]
                    # write a message from queue to all known clients who are ready
                    for w in writable:
                        w.send(str.encode(
                            sendMessage[0] + "> " + sendMessage[1] + "\n"))
                    # write a message from queue to all known nodes
                    if myComp not in listener.chatNodes:
                        for node in list(listener.chatNodes):
                            serverMsgA = {
                                "command": "MSG", "user": sendMessage[0], "message": sendMessage[1]}
                            serverMsgA = json.dumps(serverMsgA)
                            server.sendto(
                                str.encode(serverMsgA), (listener.chatNodes[node]["addresses"], listener.chatNodes[node]["port"]))

                # ---------------------------------------------------------
                for s in exceptional:
                    inputs.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                        s.close()

            # all the time related function calls
            clockTime = int(time.time())
            checkPingStatus()
            if clockTime > 55 + prevTime:
                prevTime = clockTime
                sendPing()
    except KeyboardInterrupt:
        exit_server()
        sys.exit(0)


# call to function to get the node listening
waitForConnections()

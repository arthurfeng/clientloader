'''
Created on 2014-2-21

@author: fengjian
'''
try:
    from src import flash, hls, real, dash, mms
except:
    from src import flash, hls, real, dash
from src.libs import mythread
#import matplotlib.pyplot as plt
import multiprocessing
import random
import os
import re
import sys
import uuid
import time
import xmlrpclib
import urlparse
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

CLIENTSTATUS = dict()
X_PLOT = list()
Y_PLOT = list()
RPC_PORT = 8000
USERNAME = "xing"
PASSWD = "123"
AUTH = False

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


def add_flash_client(task_uuid, url):
    
    client = multiprocessing.Process(target=flash.connect, args=(url,), name="rtmp,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[task_uuid][client_uuid] = client
        time.sleep(0.5)
    else:
        add_flash_client(url)

def add_hls_client(task_uuid, url):
    
    client = multiprocessing.Process(target=hls.connect, args=(url,), name="hls,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[task_uuid][client_uuid] = client
        time.sleep(0.5)
    else:
        add_hls_client(url)

def add_dash_client(task_uuid, url):
    
    client = multiprocessing.Process(target=dash.connect, args=(url,), name="dash,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[task_uuid][client_uuid] = client
        time.sleep(0.5)
    else:
        add_dash_client(url)

def add_real_client(task_uuid, url):
    
    client = multiprocessing.Process(target=real.connect, args=(url,), name="rtsp,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[task_uuid][client_uuid] = client
        time.sleep(0.5)
    else:
        add_real_client(url)

def add_mms_client(task_uuid, url):
    
    client = multiprocessing.Process(target=mms.connect, args=(url,), name="mms,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[task_uuid][client_uuid] = client
        time.sleep(0.5)
    else:
        add_mms_client(url)
########################################################### OPEN FUNCTION ###########################################################

def start_client(task_uuid, url, client_number):
    
    if not task_uuid:
        task_uuid = str(uuid.uuid1())
    if not task_uuid in CLIENTSTATUS.keys():
        CLIENTSTATUS[task_uuid] = {}
    if re.match("rtmp://", url):
        for i in range(client_number):
            add_flash_client(task_uuid, url)
    elif re.search(".m3u8", url) or re.search("m3ugen", url):
        for i in range(client_number):
            add_hls_client(task_uuid, url)
    elif re.match("rtsp://", url):
        for i in range(client_number):
            add_real_client(task_uuid, url)
    elif re.match("dashgen", url) or re.search("bmff", url) or re.search("mpd", url):
        for i in range(client_number):
            add_dash_client(task_uuid, url)
    elif re.match("mms://", url):
        for i in range(client_number):
            add_mms_client(task_uuid, url)
    return check_clients_status(task_uuid)

def check_stop_clients_number(task_uuid, restart_client_on_failure=False):
    
    if task_uuid not in CLIENTSTATUS.keys():
        return 0
    failed_client_number = 0
    for uuid in CLIENTSTATUS[task_uuid].keys():
        client = CLIENTSTATUS[task_uuid][uuid]
        if not client.is_alive():
            if restart_client_on_failure:
                if CLIENTSTATUS[task_uuid].pop(uuid, None):
                    start_client(task_uuid, client.name.split(",")[-1], 1)
            failed_client_number += 1
    return failed_client_number
            
def check_clients_number(task_uuid):
    
    if not task_uuid:
        num = 0
        for i in CLIENTSTATUS.keys():
            num += len(CLIENTSTATUS[i].keys())
        return num
    if task_uuid not in CLIENTSTATUS.keys():
        return 0
    return len(CLIENTSTATUS[task_uuid].keys())

def check_alive_clients(task_uuid):
    
    if task_uuid not in CLIENTSTATUS.keys():
        return 0
    alive_client_number = 0
    for client in CLIENTSTATUS[task_uuid].values():
        if client.is_alive():
            alive_client_number += 1
    return alive_client_number

def check_taskid_number():
    
    return len(CLIENTSTATUS.keys())

def check_clients_status(task_uuid, restart_client_on_failure=False):
    
    if task_uuid not in CLIENTSTATUS.keys():
        return 0,0,0,0
    return task_uuid, check_stop_clients_number(task_uuid, restart_client_on_failure), \
        check_alive_clients(task_uuid), check_clients_number(task_uuid)

def check_task_status():
    
    return CLIENTSTATUS.keys()

def stop_client(client):
    
    client.terminate()
    time.sleep(0.1)
    if client.is_alive():
        stop_client()
    return True

def stop_clients(task_uuid, clients_number=0, random_stop=1, client_type=None):
    
    if task_uuid not in CLIENTSTATUS.keys():
        return False
    if random_stop and not client_type:
        TIMER = len(CLIENTSTATUS[task_uuid].keys())
        while TIMER:
            client = random.choice(CLIENTSTATUS[task_uuid].values())
            if stop_client(client):
                clients_number -= 1
            if clients_number == 0:
                return True
            TIMER -= 1
    for client in CLIENTSTATUS[task_uuid].values():
        if client_type and client.is_alive() and client.name.split(",")[0].lower() == client_type:
            if stop_client(client):
                clients_number -= 1
        if clients_number == 0:
            return True

def stop_force(task_uuid):
    
    if task_uuid not in CLIENTSTATUS.keys():
        return False
    for client in CLIENTSTATUS[task_uuid].values():
        stop_client(client)
    CLIENTSTATUS.pop(task_uuid)
    #print CLIENTSTATUS.keys()
    return True
    
def clear_clients():
    
    for clientid in CLIENTSTATUS.values():
        for client in clientid.values():
            stop_client(client)
    CLIENTSTATUS.clear()
    return True

def doServer():
    server = SimpleXMLRPCServer(("192.168.36.16", RPC_PORT), allow_none=True)
                            #requestHandler=RequestHandler)
    print "Listening on port %s..." % RPC_PORT
    server.register_function(start_client, "start_client")
    server.register_function(check_clients_status, "check_clients_status")
    server.register_function(check_task_status, "check_task_status")
    server.register_function(stop_clients, "stop_clients")
    server.register_function(stop_force, "stop_force")
    server.register_function(clear_clients, "clear_clients")
    server.register_function(check_clients_number, "check_clients_number")
    server.serve_forever()

if __name__ == '__main__':
    
    try:
        
        doServer()
    except Exception, e:
        print e
    finally:
        clear_clients()

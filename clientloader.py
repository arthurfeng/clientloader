'''
Created on 2014-2-21

@author: fengjian
'''
from src import flash, hls, real
from src.libs import mythread
import multiprocessing
import random
import os
import re
import sys
import uuid
import time
import urlparse
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

CLIENTSTATUS = dict()

def add_flash_client(url):
    
    client = multiprocessing.Process(target=flash.connect, args=(url,), name="rtmp,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[client_uuid] = client
        time.sleep(0.5)
    else:
        add_flash_client(url)

def add_hls_client(url):
    
    client = multiprocessing.Process(target=hls.connect, args=(url,), name="hls,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[client_uuid] = client
        time.sleep(0.5)
    else:
        add_hls_client(url)

def add_real_client(url):
    
    client = multiprocessing.Process(target=real.connect, args=(url,), name="rtsp,%s" % url)
    client.start()
    if client.is_alive():
        client_uuid = str(uuid.uuid1())
        CLIENTSTATUS[client_uuid] = client
        time.sleep(0.5)
    else:
        add_real_client(url)

def start_client(url, client_number):
    
    if re.match("rtmp://", url):
        for i in range(client_number):
            add_flash_client(url)
    elif re.search(".m3u8", url) or re.search("m3ugen", url):
        for i in range(client_number):
            add_hls_client(url)
    elif re.match("rtsp://", url):
        for i in range(client_number):
            add_real_client(url)

def check_stop_clients_number(restart_client_on_failure=False):
    
    failed_client_number = 0
    for uuid in CLIENTSTATUS.keys():
        client = CLIENTSTATUS[uuid]
        if not client.is_alive():
            if restart_client_on_failure:
                if CLIENTSTATUS.pop(uuid, None):
                    start_client(client.name.split(",")[-1], 1)
            failed_client_number += 1
    return failed_client_number
            
def check_clients_number():
    
    return len(CLIENTSTATUS.keys())

def check_alive_clients():
    
    alive_client_number = 0
    for client in CLIENTSTATUS.values():
        if client.is_alive():
            alive_client_number += 1
    return alive_client_number

def stop_client(client):
    
    client.terminate()
    time.sleep(0.1)
    if client.is_alive():
        stop_client()
    return True

def stop_clients(clients_number=0, random_stop=1, client_type=None):
    
    if random_stop and not client_type:
        TIMER = len(CLIENTSTATUS.keys())
        while TIMER:
            client = random.choice(CLIENTSTATUS.values())
            if stop_client(client):
                clients_number -= 1
            if clients_number == 0:
                return
            TIMER -= 1
    for client in CLIENTSTATUS.values():
        if client_type and client.is_alive() and client.name.split(",")[0].lower() == client_type:
            if stop_client(client):
                clients_number -= 1
        if clients_number == 0:
            return

def stop_force():
    
    for client in CLIENTSTATUS.values():
        stop_client(client)
    CLIENTSTATUS.clear()

class ClientServer(SimpleHTTPRequestHandler):
    
    __data__buffer = ""
    
    def do_GET(self):
        """Serve a GET request."""
        f = self.send_data()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
            
    def parse_url(self):
        
        client_url = None
        client_number = 1
        client_type = None
        random_stop = True
        restart_on_failed = False
        parsed_url = urlparse.urlparse(self.path)
        request_type = os.path.split(parsed_url.path)[-1]
        for query in parsed_url.query.split("&"):
            parameter = query.split("=")
            if parameter[0].lower() == "url":
                client_url = parameter[-1]
            elif parameter[0].lower() == "number":
                client_number = int(parameter[-1])
            elif parameter[0].lower() == "randomstop":
                random_stop = int(parameter[-1])
            elif parameter[0].lower() == "clienttype":
                client_type = parameter[-1]
            elif parameter[0].lower() == "restart":
                restart_on_failed = int(parameter[-1])
        if request_type == "add_client.html":
            start_client(client_url, client_number)
            self.__data_buffer = "%s,%s\n" % (check_alive_clients(), client_url)
            return True
        elif request_type == "del_client.html":
            stop_clients(client_number, random_stop, client_type)
            self.__data_buffer = "%s\n" % check_stop_clients_number(False)
            return True
        elif request_type == "status_client.html":
            failed_number = check_stop_clients_number(restart_on_failed)
            alive_number = check_alive_clients()
            all_number = check_clients_number()
            self.__data_buffer = "%s,%s,%s\n" % (failed_number, alive_number, all_number)
            return True
        elif request_type == "clear_client.html":
            stop_force()
            self.__data_buffer = "%s\n" % check_stop_clients_number(False)
            return True
        return False
        
    def send_data(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
            f.close()
        except IOError:
            self.send_error(404, "File not found")
            return None
        f = StringIO()
        self.send_response(200)
        if not self.parse_url():
            return None
        f.write(self.__data_buffer)
        length = f.tell()
        f.seek(0)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

def start(HandlerClass = ClientServer,
         ServerClass = BaseHTTPServer.HTTPServer):
    BaseHTTPServer.test(HandlerClass, ServerClass)

if __name__ == '__main__':
    
    try:
        print start()
    except Exception, e:
        print e
    finally:
        stop_force()

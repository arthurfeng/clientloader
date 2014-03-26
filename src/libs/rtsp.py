'''
Created on 2014-2-20

@author: fengjian
'''
import urlparse
import socket
import struct
import hashlib
import base64
import re
import time
import random
import os

class rtsplib():

    __sendbuffer = ''  # Buffer from which lines are parsed
    sendmsg = ''
    length = None
    __session = None  # RTSP Session
    __etag = None
    cseq = 1
    response_status = {
        "Timeout": 79
    }

    def sendLine(self, line):

        self.__sendbuffer = self.__sendbuffer + line + "\r\n"
        if line == "":
            self.sendmsg = self.__sendbuffer
            self.__sendbuffer = ""

    def sendCommand(self, command, path):
        """ Sends off an RTSP command
        These appear at the beginning of RTSP headers """
        self.sendLine('%s %s RTSP/1.0' % (command, path))

    def sendHeader(self, name, value):
        """ Sends off a header, same method as HTTP headers """
        self.sendLine('%s: %s' % (name, value))

    def sendHeaders(self, dict):
        if not dict:
            return
        for key, value in dict.items():
            self.sendHeader(key, value)

    def endHeaders(self):
        """ Sends \r\n which signifies the end of the headers """
        self.sendLine('')

    def sendMethod(self, method, target='*', headers=None):
        self.sendCommand(method, target)
        self.sendHeader('CSeq', self.cseq)
        self.cseq += 1
        self.sendHeaders(headers)
        self.endHeaders()

    # -----------------
    # Response Handlers
    # -----------------

    def handleResponse(self, data):

        """Called when get response from rtsp server"""
        lines = data.split("\r\n")
    #    print lines
        for i in lines:
            line = i.split(":")
            if line[0].startswith("RTSP/1.0"):
                self.response_status["status"] = (int(line[-1].split(" ")[1]),
                                " ".join(line[-1].split(" ")[2:]))
            if line[0] == "CSeq":
                self.response_status["cseq"] = line[-1]
            elif line[0] == "Public":
                self.response_status["options"] = line[-1].split(",")
            elif line[0] == "Transport":
                self.response_status["Platload"] = line[-1].split(";")[0].strip()
                if self.response_status["Platload"].find("real") > 0:
                    self.response_status["ClientPort"] = line[-1].split(";")[1].split("-")[0]
                    self.response_status["ServerPort"] = line[-1].split(";")[2].split("-")[0]
                else:
                    if self.response_status["Platload"] == "x-pn-tng/tcp":
                        self.response_status["interleaved"] = line[-1].split(";")[-1]
                    else:
                        self.response_status["TransportType"] = line[-1].split(";")[1]
                        self.response_status["ClientPort"] = line[-1].split(";")[2].split("-")[0]
                        self.response_status["ServerPort"] = line[-1].split(";")[3].split("-")[0]
            elif line[0] == "Session":
                value = line[-1]
                session_timeout = value.split(";")
                self.response_status["Session"] = session_timeout[0]
                self.__session = session_timeout[0].strip()
                if len(session_timeout) == 2 and session_timeout[-1].split("=")[0].lower() == "timeout":
                    self.response_status["Timeout"] = int(session_timeout[-1].split("=")[-1])
            elif line[0] == "RealChallenge1":
                self.response_status["RealChallenge1"] = line[-1].strip()
            elif line[0] == "ETag":
                self.__etag = line[-1].strip()
                self.response_status["ETag"] = self.__etag
            elif line[0] == "x-predecbufsize":
                self.response_status["predecbufsize"] = line[-1].strip()
            elif line == "":
                break
    # ----------------------
    # Packet Sending Methods
    # ----------------------

    def sendOptions(self, target='*', headers=None):
        """ Requests available OPTIONS from server """
        self.sendMethod('OPTIONS', target, headers)

    def sendDescribe(self, target='*', headers=None):
        """ Asks server to describe stream in sdp format """
        self.sendMethod('DESCRIBE', target, headers)

    def sendSetup(self, target='*', headers=None):
        """ Tells the server to setup the stream """
        if self.__etag:
            headers["If-Match"] = self.__etag
        else:
            if self.__session:
                headers['Session'] = self.__session
        self.sendMethod('SETUP', target, headers)

    def sendSetParameter(self, target='*', headers=None):
        """ Tells the server to set parameters for streaming """
        if self.__session:
            headers['Session'] = self.__session
        self.sendMethod('SET_PARAMETER', target, headers)

    def sendPlay(self, range, target='*', headers={}):
        """ Tells the server to play the stream for you """
        if self.__session:
            headers['Session'] = self.__session
        headers['Range'] = "npt=%s" % range
        self.sendMethod('PLAY', target, headers)

    def sendGetParameter(self, target='*', headers=None):
        """ Tells the server to maintan the session """
        if self.__session:
            headers['Session'] = self.__session
        self.sendMethod('GET_PARAMETER', target, headers)

    def sendTearDown(self, target='*', headers=None):

        if self.__session:
            headers['Session'] = self.__session
        self.sendMethod('TEARDOWN', target, headers)


def rn5_auth(username, realm, password, nonce, uuid):
    MUNGE_TEMPLATE ='%-.200s%-.200s%-.200sCopyright (C) 1995,1996,1997 RealNetworks, Inc.'
    authstr ="%-.200s:%-.200s:%-.200s" % (username, realm, password)
    first_pass = hashlib.md5(authstr).hexdigest()

    munged = MUNGE_TEMPLATE % (first_pass, nonce, uuid)
    return hashlib.md5(munged).hexdigest()

class RealChallenge():
    XOR_TABLE = [ 0x05, 0x18, 0x74, 0xd0, 0x0d, 0x09, 0x02, 0x53, 0xc0, 0x01,
                  0x05, 0x05, 0x67, 0x03, 0x19, 0x70, 0x08, 0x27, 0x66, 0x10,
                  0x10, 0x72, 0x08, 0x09, 0x63, 0x11, 0x03, 0x71, 0x08, 0x08,
                  0x70, 0x02, 0x10, 0x57, 0x05, 0x18, 0x54 ]
    def AV_WB32(d):
        """ Used by RealChallenge() """
        d = d.decode('hex')
        return list(struct.unpack('%sB' % len(d), d))

    def compute(rc1):
        """ Translated from MPlayer's source
        Computes the realchallenge response and checksum """
        buf = list()
        buf.extend( RealChallenge.AV_WB32('a1e9149d') )
        buf.extend( RealChallenge.AV_WB32('0e6b3b59') )

        rc1 = rc1.strip()

        if rc1:
            if len(rc1) == 40: rc1 = rc1[:32]
            if len(rc1) > 56: rc1 = rc1[:56]
            buf.extend( [ ord(i) for i in rc1 ] )
            buf.extend( [ 0 for i in range(0, 56 - len(rc1)) ] )

        # xor challenge bytewise with xor_table
        for i in range(0, len(RealChallenge.XOR_TABLE)):
            buf[8 + i] ^= RealChallenge.XOR_TABLE[i];

        sum = hashlib.md5( ''.join([ chr(i) for i in buf ]) )

        response = sum.hexdigest() + '01d0a8e3'

        chksum = list()
        for i in range(0, 8):
            chksum.append(response[i * 4])
        chksum = ''.join(chksum)

        return (response, chksum)
    compute = staticmethod(compute)
    AV_WB32 = staticmethod(AV_WB32)


class Rtsp():

    RTSPPort = 554
    RTSPProtocol = "tcp"
    RTPProtocol = "udp"
    Transport = "unicast"
    Payload = "RTP/AVP"
    RDT = False
    VOD = False
    GUID = "00000000-0000-0000-0000-000000000000"
    CLIENT_CHALLENGE = '9e26d33f2984236010ef6253fb1887f7'
    PLAYER_START_TIME = '[28/03/2003:22:50:23 00:00]'
    companyID = 'KnKV4M4I/B2FjJ1TToLycw=='
    agent = 'RealMedia Player Version 6.0.9.1235 (linux-2.0-libc6-i386-gcc2.95)'
    clientID = 'Linux_2.4_6.0.9.1235_play32_RN01_EN_586'
    bandwidth = 999999


    data_received = 0
    out_file = None
    prev_timestamp = None
    prev_stream_num = None
    streamids = []
    setup_streamids = []
    ended_streamids = []

    sent_options = False
    sent_describe = False
    sent_parameter = False
    sent_bandwidth = False
    sent_realchallenge2 = False
    sent_rn5_auth = False
    rn5_authdata = None

    def __init__(self):

        self.len = 10240
        self.user_agent = "HelixAT.library.function.myrtsp"
        self.rtsplib = rtsplib()
        self.session_server_list = list()

    def set_url(self, url):
        """ Parses given url into username, password, host, and port """
        self.target = url
        self.url = url
        parsed_url = urlparse.urlsplit(url)
        self.scheme, self.netloc, self.path, self.query, self.fragment = parsed_url
        self.username = parsed_url.username
        self.password = parsed_url.password
        self.rtspport = parsed_url.port
        if self.rtspport is None:
            self.rtspport = self.RTSPPort
        if os.path.split(self.path)[-1].endswith(".rm"):
            self.RDT = True

    def rtsp_conn(self):

        try:
            if self.RTSPProtocol == "tcp":
                self.rtsp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                self.rtsp_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtsp_conn.connect((self.netloc, self.rtspport))
            return 0, "Make RTSP Connection Success"
        except Exception, e:
            return 100, "function-myrtsp-myrtsp-rtsp_conn: %s" % e

    def gen_OPTIONS(self):

        Header = {}
        Header["User-Agent"] = self.user_agent
        if self.RDT:
            Header['ClientChallenge'] = self.CLIENT_CHALLENGE
            Header['PlayerStarttime'] = self.PLAYER_START_TIME
            Header['CompanyID'] = self.companyID
            Header['GUID'] = self.GUID
            Header['RegionData'] = '0'
            Header['ClientID'] = self.clientID
            Header['Pragma'] = 'initiate-session'
        self.rtsplib.sendOptions("rtsp://%s:%s" % (self.netloc, self.rtspport), headers=Header)
        return self.rtsplib.sendmsg

    def send_OPTIONS(self):

        smsg = self.gen_OPTIONS()
        self.rtsp_conn.send(smsg)
        time.sleep(0.1)
        rmsg = self.rtsp_conn.recv(self.len)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send OPTIONS Request Success"
        else:
            return status, "Send OPTIONS Request Failed, Recode Code: %s" % status[-1]

    def gen_DESCRIBE(self):

        Header = {}
        Header["User-Agent"] = self.user_agent
        Header["Accept"] = "application/sdp"
        if self.RDT:
            Header['GUID'] = self.GUID
            Header['RegionData'] = '0'
            Header['ClientID'] = self.clientID
            Header['SupportsMaximumASMBandwidth'] = '1'
            Header['Language'] = 'en-US'
            Header['Require'] = 'com.real.retain-entity-for-setup'
            ##rn5 auth
            if self.rn5_authdata:
                authstring ='RN5 '
                self.rn5_authdata['username'] = self.username
                self.rn5_authdata['GUID'] = '00000000-0000-0000-0000-000000000000'
                self.rn5_authdata['response'] = \
                             rn5_auth(nonce=self.rn5_authdata['nonce'],
                             username=self.username,
                             password=self.password,
                             uuid=self.rn5_authdata['GUID'],
                             realm=self.rn5_authdata['realm'])
                ## a string like 'RN5 username="foo",realm="bla"...'
                Header['Authorization'] = 'RN5 ' + ', '.join(
                    ['%s="%s"' % (key, val) for key,val in self.rn5_authdata.items()])
            if not self.rn5_authdata and self.username is not None:
                authstr = '%s:%s' % (self.username,
                                     self.password
                                     if self.password else '')
                authstr = base64.b64encode(authstr)
                Header['Authorization'] = 'Basic %s' % authstr
        self.rtsplib.sendDescribe(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_DESCRIBE(self):

        smsg = self.gen_DESCRIBE()
        self.rtsp_conn.send(smsg)
        time.sleep(0.1)
        rmsg = self.rtsp_conn.recv(self.len)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send DESCRIBE Request Success", rmsg
        else:
            return status[0], "Send DESCRIBE Request Failed, Recode Code: %s" % status[-1], 0

    def gen_SETUP(self, streamid):

        while True:
            port = random.randint(5000, 65535)
            if self.RDT or not self.rtp_session_server_udp(port):
                break
        client_port = "%s-%s" % (port, port + 1)
        Header = {}
        Header["User-Agent"] = self.user_agent
        if self.RDT:
            if not self.sent_realchallenge2:
                self.sent_realchallenge2 = True
                challenge_tuple = RealChallenge.compute(self.rtsplib.response_status["RealChallenge1"])
                Header['RealChallenge2'] = '%s, sd=%s' % challenge_tuple
            Header['Transport'] = 'x-pn-tng/tcp;mode=play,rtp/avp/tcp;unicast;mode=play'
        else:
            Header['Transport'] = "%s;%s;client_port=%s" % (self.Payload, self.Transport, client_port)
        self.rtsplib.sendSetup(self.target + "/" + streamid, headers=Header)
        return self.rtsplib.sendmsg

    def send_SETUP(self, streamid):

        smsg = self.gen_SETUP(streamid)
        self.rtsp_conn.send(smsg)
        rmsg = self.rtsp_conn.recv(self.len)
        time.sleep(0.1)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send SETUP Request Success"
        else:
            return status[0], "Send SETUP Request Failed, Recode Code: %s" % status[1]

    def gen_PLAY(self, Range):

        Header = {}
        Header["User-Agent"] = self.user_agent
        self.rtsplib.sendPlay(Range, self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_PLAY(self, Range="0.000-"):

        if Range.split("-")[-1] != "":
            self.VOD = True
            self.recive_buffer = float(Range.split("-")[-1]) * 1024
        else:
            self.recive_buffer = 1024
        smsg = self.gen_PLAY(Range)
        self.rtsp_conn.send(smsg)
        time.sleep(0.1)
        rmsg = self.rtsp_conn.recv(300)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send PLAY Request Success"
        else:
            return status[0], "Send PLAY Request Failed, Recode Code: %s" % status[1]

    def gen_SETPARAMETER(self):

        Header = {}
        Header["User-Agent"] = self.user_agent
        #Header["Content-Length"] = 2048
        Header["SetDeliveryBandwidth"] = "Bandwidth=%s;BackOff=0" % self.bandwidth
        #Header["Subscribe"] = "stream=0;rule=0,stream=0;rule=1,stream=1;rule=0,stream=1;rule=1"
        self.rtsplib.sendSetParameter(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_SETPARAMETER(self):

        smsg = self.gen_SETPARAMETER()
        self.rtsp_conn.send(smsg)
        time.sleep(0.1)
        rmsg = self.rtsp_conn.recv(1024)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send SETPARAMETER Request Success"
        else:
            return status[0], "Send SETPARAMETER Request Failed, Recode Code: %s" % status[1]

    def gen_GETPARAMETER(self):

        Header = {}
        Header["User-Agent"] =  self.user_agent
        self.rtsplib.sendGetParameter(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_GETPARAMETER(self):

        smsg = self.gen_GETPARAMETER()
        self.rtsp_conn.send(smsg)
        time.sleep(0.1)
        rmsg = self.rtsp_conn.recv(self.len)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send GETPARAMETER Request Success"
        else:
            return status[0], "Send GETPARAMETER Request Failed, Recode Code: %s" % status[1]

    def gen_TEARDOWN(self):

        Header = {}
        Header["User-Agent"] =  self.user_agent
        self.rtsplib.sendTearDown(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_TEARDOWN(self):

        try:
            smsg = self.gen_TEARDOWN()
            self.rtsp_conn.send(smsg)
            time.sleep(0.1)
            rmsg = self.rtsp_conn.recv(self.len)
            self.rtsplib.handleResponse(rmsg)
            status = self.rtsplib.response_status["status"]
            if status[0] == 200:
                return 0, "Send TEARDOWN Request Success"
            else:
                return status[0], "Send TEARDOWN Request Failed, Recode Code: %s" % status[1]
        except Exception, e:
            return 100, e
        finally:
            self.rtsp_conn.close()

    def rtp_session_server_udp(self, port):

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.bind(('', port))
            self.session_server_list.append(conn)
            return 0
        except socket.error, e:
            return 1

    def recive_stream(self):
        
        if self.RDT is True:
            return self.recive_rdt()
        else:
            return self.recive_rtp()

    def recive_rtp(self):

        keeplive = self.rtsplib.response_status["Timeout"]
        count = 0
        try:
            while True:
                count += 1
                if keeplive - 10 == count:
                    self.send_GETPARAMETER()
                    count = 0
                for j in self.session_server_list:
                    j.settimeout(keeplive)
                    rmsg, address = j.recvfrom(int(self.recive_buffer))
                time.sleep(1)
                if self.VOD:
                    break
            return 0, "Recive RTP Package Success"
        except socket.timeout, e:
            return 1, "Recive RTP Session TimeOut"
        finally:
            self.send_TEARDOWN()
            for u in self.session_server_list:
                u.close()
   
    def recive_rdt(self):

        count = 0
        keeplive = self.rtsplib.response_status["Timeout"]
        try:
            while True:
                count += 1
                if keeplive-10 == count:
                    self.send_GETPARAMETER()
                    count = 0
                rmsg = self.rtsp_conn.recv(self.recive_buffer)
                time.sleep(1)
                if self.VOD:
                    break
            return 0, "Recive RDT Package Success"
        except socket.timeout, e:
            return 1, "Revice RDT Session TimeOut"
        finally:
            self.send_TEARDOWN()
            for u in self.session_server_list:
                u.close()

    def get_streamid_from_sdp(self, lines):
        
        streamid_list = list()
        for line in lines.split("\r\n"):
            match_streamid = re.search('streamid=(\d)', line)
            if match_streamid:
                streamid_list.append(match_streamid.group(0))
        return streamid_list
    
    def get_npt_from_sdp(self, lines):
        
        npt = "0.000-"
        for line in lines.split("\n"):
            if line.startswith("a=range:"):
                npt = line.split(":")[-1].split("=")[-1].strip("\r")
                break
        return npt.strip("\r")

if __name__ == "__main__":

    R = Rtsp()
    R.set_url("rtsp://192.168.36.159/broadcast/live")
    #R.RDT = True
    #R.VOD = True
    R.rtsp_conn()
    print R.send_OPTIONS()
    sdp = R.send_DESCRIBE()[-1]
    for i in R.get_streamid_from_sdp(sdp):
        R.send_SETUP(i)
    print R.send_SETPARAMETER()
    print R.send_PLAY()
    print R.revice_rdt(40)
    print R.send_TEARDOWN()
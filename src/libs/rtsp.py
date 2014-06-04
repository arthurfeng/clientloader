from urlparse import urlsplit
import re
import hashlib
import base64
import socket
import select
import struct
import binascii
import parse_ts
import myrtcp
import myrtp
import myrdt
import uuid
import time
import random
from md5 import md5

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
                self.response_status["predecbufsize"] = int(line[-1].strip())
            elif line[0] == "Range":
                self.response_status["Range"] = float(line[-1].strip().split("=")[-1].strip("-"))
            elif line[0] == "Reconnect":
                self.response_status["Reconnect"] = True
            elif line[0] == "Content-length":
                self.response_status["Content-length"] = int(line[-1].strip())
            elif line[0] == "WWW-Authenticate":
                self.response_status["auth-method"] = line[-1].split(" ")[0]
                match_nonce = re.search(r"nonce=\"(\d+)\"", line[-1])
                match_realm = re.search(r"realm=\"(\S+)\"", line[-1])
                if match_nonce:
                    self.response_status["nonce"] = match_nonce.group(0).split("=")[-1].strip("\"")
                if match_realm:
                    self.response_status["realm"] = match_realm.group(0).split("=")[-1].strip("\"")
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
        headers['Range'] = 'npt=%s' % range
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

        sum = md5( ''.join([ chr(i) for i in buf ]) )

        response = sum.hexdigest() + '01d0a8e3'

        chksum = list()
        for i in range(0, 8):
            chksum.append(response[i * 4])
        chksum = ''.join(chksum)

        return (response, chksum)
    compute = staticmethod(compute)
    AV_WB32 = staticmethod(AV_WB32)


class myrtsp():

    RTSPProtocol = "tcp"
    RTPProtocol = "udp"
    Transport = "unicast"
    Payload = "RTP/AVP"
    RDT = False
    VOD = False
    TsOverRTP = False
    GUID = "00000000-0000-0000-0000-000000000000"
    CLIENT_CHALLENGE = '9e26d33f2984236010ef6253fb1887f7'
    PLAYER_START_TIME = '[28/03/2003:22:50:23 00:00]'
    companyID = 'KnKV4M4I/B2FjJ1TToLycw=='
    agent = 'RealMedia Player Version 6.0.9.1235 (linux-2.0-libc6-i386-gcc2.95)'
    clientID = 'Linux_2.4_6.0.9.1235_play32_RN01_EN_586'
    bandwidth = 999999
    supported = "ABD-1.0"

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
    basic_authdata = None
    recive_data = True

    authentication = False

    def __init__(self, path, ip=None, port=None, server_name="server"):

        parsed_path = urlsplit(path)
        if parsed_path[0].lower() == "rtsp":
            if parsed_path[3]:
                path = "%s?%s" % (parsed_path[2], parsed_path[3])
            else:
                path = "%s" % parsed_path[2]
            self.ip = parsed_path[1].split(":")[0]
            self.rtspport = parsed_path[1].split(":")[-1]
            self.rtspport = 554
        if ip: self.ip = ip
        if port: self.rtspport = int(port)
        self.target = "rtsp://%s:%s%s" % (self.ip, self.rtspport, path)
        self.setURL(self.target)
        self.socket_buffer = 4096
        self.user_agent = self.agent
        self.rtsplib = rtsplib()
        self.rtp_session_server_list = list()
        self.rtcp_session_server_list = list()

    def setURL(self, url):
        """ Parses given url into username, password, host, and port """
        self.url = url
        parsed_url = urlsplit(url)
        self.scheme, self.netloc, self.path, self.query, self.fragment = parsed_url

        self.username = parsed_url.username
        self.password = parsed_url.password

    def receive_rtsp(self, continue_receive=True):

        try:
            #the_socket.setblocking(0)
            total_data=[];data=''
            while True:
                r,w,x = select.select([self.rtsp_conn],[],[],0.05)
                if len(r)>0:
                    data = r[0].recv(self.socket_buffer)
                    total_data.append(data)
                else:
                    break
                if not continue_receive:
                    break
            if total_data:
                return ''.join(total_data)
            else:
                return self.receive_rtsp()
        except Exception, e:
            return "%s" % e

    def send_rtsp(self, smsg):

        try:
            self.rtsp_conn.send(smsg)
            return True
        except Exception, e:
            return False

    def rtsp_conn(self):

        try:
            if self.RTSPProtocol == "tcp":
                self.rtsp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            elif self.RTSPProtocol == "udp":
                self.rtsp_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtsp_conn.connect((self.ip, self.rtspport))
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
            Header["Supported"] = self.supported
        self.rtsplib.sendOptions(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_OPTIONS(self):

        smsg = self.gen_OPTIONS()
        if not self.send_rtsp(smsg):
            return 1, "Send Msg To Helix Server Failed"
        time.sleep(0.1)
        rmsg = self.receive_rtsp()
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
            Header['Language'] = 'zh-CN, zh, *'
            Header['Require'] = 'com.real.retain-entity-for-setup'
            ##rn5 auth
            if self.rn5_authdata:
                authstring ='RN5 '
                self.rn5_authdata['username'] = self.username
                self.rn5_authdata['GUID'] = str(uuid.uuid1())
                self.rn5_authdata['response'] = \
                         rn5_auth(nonce=self.rn5_authdata['nonce'],
                         username=self.username,
                         password=self.password,
                         uuid=self.rn5_authdata['GUID'],
                         realm=self.rn5_authdata['realm'])
                ## a string like 'RN5 username="foo",realm="bla"...'
                Header['Authorization'] = 'RN5 ' + ', '.join(
                        ['%s="%s"' % (key, val) for key,val in self.rn5_authdata.items()])
        if self.basic_authdata:
            authstr = '%s:%s' % (self.username,
                                 self.password
                                 if self.password else '')
            authstr = base64.b64encode(authstr)
            Header['Authorization'] = 'Basic %s' % authstr
        self.rtsplib.sendDescribe(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_DESCRIBE(self):

        smsg = self.gen_DESCRIBE()
        if not self.send_rtsp(smsg):
            return 1, "Send Msg To Helix Server Failed"
        time.sleep(0.1)
        rmsg_buffer = self.receive_rtsp()
        tmp = rmsg_buffer.split("\r\n\r\n", 1)
        header = tmp[0].strip()
        self.sdpdata = tmp[-1].strip()
        self.rtsplib.handleResponse(header)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send DESCRIBE Request Success", self.sdpdata
        elif status[0] == 401 and self.authentication:
            self.rn5_authdata = {
                                "realm":self.rtsplib.response_status["realm"],
                                "nonce":self.rtsplib.response_status["nonce"]}
            self.authentication = False
            return self.send_DESCRIBE()
        else:
            return status[0], "Send DESCRIBE Request Failed, Recode Code: %s" % status[-1], 0

    def gen_SETUP(self, id):

        while True:
            rtp_port = random.randrange(1026, 65535, 2)
            rtcp_port = rtp_port + 1
            if not self.rtp_session_server_udp(rtp_port) and \
                                                        not self.rtcp_session_server_upd(rtcp_port):
                break
        client_port = "%s-%s" % (rtp_port, rtcp_port)
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
        self.rtsplib.sendSetup(self.target + "/" + id, headers=Header)
        return self.rtsplib.sendmsg

    def send_SETUP(self, id):

        smsg = self.gen_SETUP(id)
        if not self.send_rtsp(smsg):
            return 1, "Send Msg To Helix Server Failed"
        rmsg = self.receive_rtsp()
        time.sleep(0.1)
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            return 0, "Send SETUP %s Request Success" % id
        else:
            return status[0], "Send SETUP %s Request Failed, Recode Code: %s" % (id, status[1])

    def gen_PLAY(self, Range):

        Header = {}
        Header["User-Agent"] = self.user_agent
        self.rtsplib.sendPlay(Range, self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_PLAY(self, Range="0.000-", Bookmarking=None):

        self.rdt_data_buffer = ""
        smsg = self.gen_PLAY(Range)
        if not self.send_rtsp(smsg):
            return 1, "Send Msg To Helix Server Failed"
        time.sleep(0.1)
        rmsg_buffer = self.receive_rtsp(False)
        rmsg = rmsg_buffer.split("\r\n\r\n")[0].strip()
        self.rdt_data_buffer = rmsg_buffer.split("\r\n\r\n")[-1]
        self.rtsplib.handleResponse(rmsg)
        status = self.rtsplib.response_status["status"]
        if status[0] == 200:
            if Bookmarking:
                if self.rtsplib.response_status.get("Range", None) != None:
                    start_time = self.rtsplib.response_status["Range"]
                    if abs(int(start_time)-int(Bookmarking)) > 2:
                        return 2, "Bookmarking options failed, should be start with %s not %s" % (Bookmarking, start_time)
                    else:
                        return 0, "Send Play Success, Bookmaring start with %s" % Bookmarking
                else:
                    return 3, "Send Play Success, Bookmarking request failed, need Range in PLAY response msg"
            return 0, "Send PLAY Request Success"
        else:
            return status[0], "Send PLAY Request Failed, Recode Code: %s" % status[1]

    def gen_SETPARAMETER(self):

        Header = {}
        Header["User-Agent"] = self.user_agent
        Header["SetDeliveryBandwidth"] = "Bandwidth=%s;BackOff=0" % self.bandwidth
        Header["Subscribe"] = "stream=0;rule=0,stream=0;rule=1,stream=1;rule=0,stream=1;rule=1"
        self.rtsplib.sendSetParameter(self.target, headers=Header)
        return self.rtsplib.sendmsg

    def send_SETPARAMETER(self):

        smsg = self.gen_SETPARAMETER()
        if not self.send_rtsp(smsg):
            return 1, "Send Msg To Helix Server Failed"
        time.sleep(0.1)
        rmsg = self.receive_rtsp()
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
        if not self.send_rtsp(smsg):
            return 1, "Send Msg To Helix Server Failed"
        time.sleep(0.1)
        rmsg = self.receive_rtsp()
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
            if not self.send_rtsp(smsg):
                return 1, "Send Msg To Helix Server Failed"
            time.sleep(0.1)
            rmsg = self.receive_rtsp()
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

    def rtp_session_server_multicast_udp(self, ip, port):

        try:
            total_data=[];data=''
            COUNTER = 20
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('', port))
            mreq = struct.pack("=4sl", socket.inet_aton(ip), socket.INADDR_ANY)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            while COUNTER:
                r,w,x = select.select([s],[],[],0.05)
                if len(r)>0:
                    data = r[0].recv(self.socket_buffer)
                    total_data.append(data)
                else:
                    break
                COUNTER -= 1
            return 0, "Receive Multicast Stream IP: %s, Port: %s Success" % (ip, port)
        except socket.timeout, e:
            return 1, "Recive RTP Session TimeOut"
        except Exception, e:
            return 100, "function-myrtsp-myrtsp-rtp_session_server_multicast_udp: %s" % e
        finally:
            s.close()

    def rtp_session_server_udp(self, port):

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.bind(('', port))
            #conn.setblocking(False)
            #conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.rtp_session_server_list.append(conn)
            return 
        except socket.error, e:
            return 1

    def rtcp_session_server_upd(self, port):

        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.bind(('', port))
            #conn.setblocking(False)
            #conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.rtcp_session_server_list.append(conn)
            return 0
        except socket.error, e:
            return 1

    def revice_rtp(self):

        rtcp = myrtcp.RTCPDatagram()
        rtp = myrtp.RTPDatagram()
        keeplive = self.rtsplib.response_status["Timeout"]
        count = 0
        try:
            while True:
                count += 1
                for rtcp_conn in self.rtcp_session_server_list:
                    rtcp_rmsg, address = rtcp_conn.recvfrom(self.socket_buffer)
                    rtcp.Datagram = rtcp_rmsg
                    rtcp.parse()
                    smsg = rtcp.generateRR()
                    rtcp_conn.sendto(smsg, address)
                    if rtcp.GoodBye:
                        return 0, "Recive GoodBye Msg, End Connection"
                if keeplive - 10 == count:
                    self.send_GETPARAMETER()
                    count = 0
                for rtp_conn in self.rtp_session_server_list:
                    rtp_rmsg, address = rtp_conn.recvfrom(self.socket_buffer)
                    if len(rtp_rmsg)>0:
                        rtp.parse(rtp_rmsg)
#                         if self.TsOverRTP:
#                             ts_parser = parse_ts.TSParser()
#                             ts_package = re.findall(r'.{188}', rtp.Payload, re.DOTALL)
#                             for i in ts_package:
#                                 if not ts_parser.isTsPackage(i):
#                                     return 2, "Ts Package Is Not Standard"
                time.sleep(0.1)
            return 0, "Recive RTP Package Success"
        except socket.timeout, e:
            return 1, "Recive RTP Session TimeOut"
        finally:
            for u in self.rtp_session_server_list:
                u.close()
            for u in self.rtcp_session_server_list:
                u.close()
   
    def revice_rdt(self):

        rdt = myrdt.RDTDatagram()
        count = 0
        keeplive = self.rtsplib.response_status["Timeout"]
        data_buffer_size = self.rtsplib.response_status.get("predecbufsize", 0)
        try:
            while True:
                count += 1
                if keeplive-10 == count:
                    self.send_GETPARAMETER()
                    count = 0
                rmsg = self.receive_rtsp(False)
                if self.rdt_data_buffer:
                    rmsg = "%s%s" % (self.rdt_data_buffer, rmsg)
                    self.rdt_data_buffer = ""
                if rmsg == "":
                    return 0, "Receive RDT Package Failed, Not RDT Package Receiced"
                ## can't understand the rdt package TODO ##
                rdt.parse(self.sdpdata, rmsg)
                if data_buffer_size - rdt.data_size < 0:
                    return 0, "End Recive Streaming"
                time.sleep(1)
            return 0, "Recive RDT Package Success"
        except socket.timeout, e:
            return 1, "Revice RDT Session TimeOut"
        except KeyError, e:
            # FOR SureStream live source, we can't parse it, so raise a KeyError TODO
            return 0, "Recive RDT Success"
        except IndexError, e:
            # FOR SureStream live source, we can't parse it, so raise a IndexError TODO
            return 0, "Recive RDT Success"
        finally:
            rdt.close()

    def stop(self):

        RUN = False


if __name__ == "__main__":

    R = myrtsp("rtsp://192.168.36.161:554/segsrc/meet.mp4")
    R.rtsp_conn()
    print R.send_OPTIONS()
    print R.send_DESCRIBE()
    print R.send_SETUP("streamid=1")
    print R.send_SETUP("streamid=2")
    print R.send_SETPARAMETER()
    print R.send_PLAY("0.000-")
    print R.revice_rtp()
    print R.send_TEARDOWN()

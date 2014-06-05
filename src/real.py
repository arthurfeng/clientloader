'''
Created on 2014-2-20

@author: fengjian
'''
from libs import rtsp, parse_sdp, log
import re

Logger = log.Log()

class RTSPError(Exception):
    
    def __init__(self, response, url): 
        Exception.__init__(self)
        self.response = response
        self.url = url

class Real():
    
    def play(self, url):
        
        RTSP = rtsp.myrtsp(url)
        if url.split("/")[-1].endswith(".rm"):
            RTSP.RDT = True
        if re.search(r"/tsrtp/", url):
            RTSP.TsOverRTP = True
        result, message = RTSP.rtsp_conn()
        result, message = RTSP.send_OPTIONS()
        result, message, sdp = RTSP.send_DESCRIBE()
        if result:
            raise RTSPError(result, url)
        sdp_parser = parse_sdp.Sdpplin(sdp)
        try: start_time = sdp_parser['StartTime']
        except: start_time = "0.000-"
        streamcount = 0
        for i in sdp_parser.streams:
            try:streamid=i["streamid"]
            except:streamid=streamcount
            result, message = RTSP.send_SETUP("streamid=%s" % streamid)
            streamcount+=1
        result, message = RTSP.send_SETPARAMETER()
        result, message = RTSP.send_PLAY(start_time)
        if RTSP.RDT:
            result, message = RTSP.revice_rdt()
        else:
            result, message = RTSP.revice_rtp()
        if result:
            raise RTSPError(result, url)
        RTSP.send_TEARDOWN()

def connect(url):
    
    try:
        real_client = Real()
        real_client.play(url)
    except RTSPError, error:
        Logger.printf("%s:%s" % (error.response, error.url), "error")
    except Exception, e:
        Logger.printf("%s" % e, "error")

if __name__ == '__main__':
    
    connect("rtsp://192.168.36.159/broadcast/live")
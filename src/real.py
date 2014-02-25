'''
Created on 2014-2-20

@author: fengjian
'''
from libs import rtsp

class RTSPError(Exception):
    
    def __init__(self, response, url): 
        Exception.__init__(self)
        self.response = response
        self.url = url

class Real():
    
    def play(self, url):
        
        rtsp_client = rtsp.Rtsp()
        rtsp_client.set_url(url)
        rtsp_client.rtsp_conn()
        result = rtsp_client.send_OPTIONS()
        if result[0]:
            raise RTSPError(result[0], url)
        sdp = rtsp_client.send_DESCRIBE()[-1]
        for i in rtsp_client.get_streamid_from_sdp(sdp):
            rtsp_client.send_SETUP(i)
        npt = rtsp_client.get_npt_from_sdp(sdp)
        rtsp_client.send_SETPARAMETER()
        rtsp_client.send_PLAY(npt)
        result = rtsp_client.recive_stream()
        if result[0]:
            raise RTSPError(result[1], url)
        return 1

def connect(url):
    
    try:
        real_client = Real()
        real_client.play(url)
    except RTSPError, error:
        print "%s:%s" % (error.response, error.url)

if __name__ == '__main__':
    
    connect("rtsp://192.168.36.159/broadcast/live")
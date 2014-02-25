'''
Created on 2014-2-20

@author: fengjian
'''
from libs import http, multitask
import time
import re

class HLSError(Exception):
    
    def __init__(self, response, url): 
        Exception.__init__(self)
        self.response = response
        self.url = url

class HLS(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.played_segment_number = 0
        
    def play(self, url):
        
        keep_play = True
        segment_url = list()
        http_request = http.Http()
        result, data, parsed_url = http_request.get1(url)
        if not result:
            raise HLSError(result, url)
        for line in data.split("\n"):
            if not line.startswith("#")  and re.search('(\d)*.ts', line):
                segment_url.append(line)
            if line.startswith("#") and re.search('EXT-X-ENDLIST', line):
                keep_play = False
            if line.startswith("#") and re.search('EXT-X-TARGETDURATION', line):
                target_duration = int(line.split(":")[-1])
        for segurl in segment_url:
            match_to_be_played_segment = re.search('\d+', segurl)
            to_be_played_segment_number = int(match_to_be_played_segment.group(0))
            if to_be_played_segment_number > self.played_segment_number:
                #print to_be_played_segment_number
                request_url = http_request.urljoin(parsed_url, segurl)
                if not http_request.get1(request_url)[0]:
                    raise HLSError(result, request_url)
            self.played_segment_number = to_be_played_segment_number
        if keep_play:
            time.sleep(target_duration)
            self.play(url)
        return 1
            
def connect(url):
    
    HLS_Client = HLS()
    HLS_Client.play(url)

if __name__ == "__main__":
    
    multitask.add(connect("http://192.168.36.159/m3ugen/broadcast/live"))
    multitask.run()
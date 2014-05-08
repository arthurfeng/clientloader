'''
Created on 2014-2-20

@author: fengjian
'''
from libs import http, multitask
import time
import re
import random

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
        self.keep_play = True
        self.target_duration = 0
        
    def single_m3u8(self, mu3u8):
        
        segment_url = list()
        for line in mu3u8.split("\n"):
            if not line.startswith("#")  and re.search('(\d)*.ts', line):
                segment_url.append(line)
            if line.startswith("#") and re.search('EXT-X-ENDLIST', line):
                self.keep_play = False
            if line.startswith("#") and re.search('EXT-X-TARGETDURATION', line):
                self.target_duration = int(line.split(":")[-1])
        return segment_url
    
    def multi_m3u8(self, m3u8):
        
        single_url_list = list()
        for line in m3u8.split("\n"):
            if line.startswith("#") and re.search('EXT-X-STREAM-INF', line):
                pass
            if not line.startswith("#") and re.search(".m3u8", line):
                single_url_list.append(line)
        return single_url_list
        
    def play(self, url):
        
        http_request = http.Http()
        result, data, parsed_url = http_request.get1(url)
        if not result:
            raise HLSError(result, url)
        single_urls = self.multi_m3u8(data)
        if single_urls:
            single_url = http_request.urljoin(parsed_url, random.choice(single_urls))
            self.play(single_url)
        segment_url = self.single_m3u8(data)
        for segurl in segment_url:
            match_to_be_played_segment = re.search('\d+', segurl)
            to_be_played_segment_number = int(match_to_be_played_segment.group(0))
            if to_be_played_segment_number > self.played_segment_number:
                #print to_be_played_segment_number
                request_url = http_request.urljoin(parsed_url, segurl)
                if not http_request.get1(request_url)[0]:
                    raise HLSError(result, request_url)
            self.played_segment_number = to_be_played_segment_number
        if self.keep_play:
            time.sleep(self.target_duration)
            self.play(url)
        return 1
            
def connect(url):
    
    try:
        HLS_Client = HLS()
        HLS_Client.play(url)
    except HLSError, error:
        print "%s:%s" % (error.response, error.url)

if __name__ == "__main__":
    
    connect("http://192.168.36.159/m3ugen/segsrc/SimpleMulti.mp4")

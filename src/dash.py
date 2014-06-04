'''
Created on 2014-5-6

@author: fengjian
'''
from libs import http, parse_dash, log
import time
import re
import random

Logger = log.Log()

class DASHError(Exception):
    
    def __init__(self, response, url): 
        Exception.__init__(self)
        self.response = response
        self.url = url
        
class DASH(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.played_segment_number = 0
        
    def play(self, url):
        
        segment_url = list()
        parse_dash_playlist = parse_dash.ParseDASH()
        http_request = http.Http()
        while True:
            result, data, parsed_url = http_request.get1(url)
            if result != 200:
                raise DASHError(result, url)
            result, message, segment_urls, dash_profile = parse_dash_playlist.start(data)
            if not segment_urls:
                raise DASHError(100, "Parse DASH MPD file Error")
            segment_url = random.choice(segment_urls)
            for segurl in segment_url:
                match_to_be_played_segment = re.search('\d+', segurl.split("/")[-1])
                to_be_played_segment_number = int(match_to_be_played_segment.group(0))
                if to_be_played_segment_number > self.played_segment_number:
                    #print to_be_played_segment_number
                    request_url = http_request.urljoin(parsed_url, segurl)
                    result, data, useless_url = http_request.get1(request_url)
                    if result != 200:
                        raise DASHError(result, request_url)
                self.played_segment_number = to_be_played_segment_number
            if parse_dash_playlist.KEEPPLAY:
                time.sleep(int(parse_dash_playlist.TIMESLEEP))
            else:
                return 1
    
def connect(url):
    
    try:
        DASH_Client = DASH()
        DASH_Client.play(url)
    except DASHError, error:
        Logger.printf("%s:%s" % (error.response, error.url), "error")

if __name__ == "__main__":
    
    connect("http://192.168.36.159/dashgen/segsrc/SimpleMulti.mp4?type=ts")
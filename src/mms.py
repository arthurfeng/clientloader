from libs import libmms, log

Logger = log.Log()

class MMSError(Exception):
    
    def __init__(self, response, url): 
        Exception.__init__(self)
        self.response = response
        self.url = url
        
class MMS():
    
    BANDWIDTH = 1e6
    
    def __init__(self):
        
        pass
    
    def play(self, url):
        
        stream = libmms.Stream()
        if not stream.run(url, self.BANDWIDTH):
            raise MMSError("404", url)
        for data in stream:
            pacake_len = len(data)
            #print data
        stream.close()

def connect(url):
    
    try:
        MMS_Client = MMS()
        MMS_Client.play(url)
    except MMSError, error:
        Logger.printf("%s:%s" % (error.response, error.url), "error")

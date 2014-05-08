'''
Created on 2014-2-20

@author: fengjian
'''
import urlparse
import httplib
import urllib2

class Http(object):
    '''
    classdocs
    '''
    header = {
              'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Cache-Control':'max-age=0',
              'Connection':'keep-alive',
              'Host':'',
              'User-Agent':'Mozilla/5.0 (Windows NT 5.1; rv:6.0.2) Gecko/20100101 Firefox/6.0.2',
              'Referer':''
              }
    
    


    def __init__(self):
        '''
        Constructor
        '''
        pass
    
    def get1(self, url):
        
        '''
        this function use httplib package
        '''
        try:
            http_conn = None
            host = urlparse.urlparse(url)
            http_conn = httplib.HTTPConnection(host.netloc)
            http_conn.request('GET', "%s?%s" % (host.path, host.query))
            response = http_conn.getresponse()
            if response.status == 200:
                data = response.read()
                if response.getheader('content_length', None):
                    content_length = response.getheader('content_length', None)
                    if len(data) != content_length:
                        return self.get1(url)
                return (1, data, url)
            elif response.status == 302:
                refer_url = response.getheader('location')
                return self.get1(refer_url)
            else:
                return (0, None, None)
        except Exception as e:
            print e
            return (0, None,None)
        finally:
            if http_conn:
                http_conn.close()

    def get2(self, url):
        
        try:
            
            host = urlparse.urlparse(url)
            header = self.header
            header['Host'] = host.netloc
            header['Referer'] = host.netloc
            
            request = urllib2.Request(url=url, headers=header)
            response = urllib2.urlopen(request)
            data = response.read()
            return (1, data)
        except urllib2.URLError, e:
            print e
            return (0, None)
        except urllib2.HTTPError, e:
            print e
            return (0, None)
            
    def urljoin(self, base, url):
        
        return urlparse.urljoin(base, url)
        
if __name__ == "__main__":
    
    http_client = Http()
    print http_client.get1("http://192.168.36.161/m3ugen/segsrc/meet.mp4")
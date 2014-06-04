'''
Created on 2014-6-4

@author: fengjian
'''
import logging

class Log(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.log = logging.getLogger('ClientLoaderTest')
        #FILENAME = self.log_path + 'robot.log'
        FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
        FILENAME = "clientloader.log"
        log_level  = "info"
        level_dic = {
            'debug':logging.DEBUG,
            'info':logging.INFO,
            'warning':logging.WARNING,
            'error':logging.ERROR,
            'critical':logging.CRITICAL
             }
        level = level_dic.get(log_level,logging.NOTSET)
        logging.basicConfig(level=level, format=FORMAT, filename=FILENAME)
    
    def printf(self, msg, level='info'):
        
        if level.lower() == 'info':
            self.log.info(msg)
        elif level.lower() == 'error':
            self.log.error(msg)
        
        
        
        
"""
MetPX Copyright (C) 2004-2006  Environment Canada
MetPX comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
"""

"""
#############################################################################################
# Name: Client.py
#
# Authors: Peter Silva (imperative style)
#          Daniel Lemay (OO style)
#          Michel Grenier (directory path with patterns)
#                         (directory path mkdir if doesn't exist)
#                         (maxLength for segmentation when needed)
#
# Date: 2005-01-10 (Initial version by PS)
#       2005-08-21 (OO version by DL)
#       2005-11-01 (Path stuff by MG)
#
# Description:
#
#############################################################################################

"""
import sys, os, re, time, fnmatch
import PXPaths
from URLParser import URLParser
from Logger import Logger
#from Flow import Flow

PXPaths.normalPaths()              # Access to PX paths

class Client(object):

    def __init__(self, name='toto', logger=None) :

        #Flow.__init__(self, name, 'sender', type, batch) # Parent constructor

        # General Attributes
        self.name = name                          # Client's name
        if logger is None:
            self.logger = Logger(PXPaths.LOG + 'tx_' + name + '.log', 'INFO', 'TX' + name) # Enable logging
            self.logger = self.logger.getLogger()
        else:
            self.logger = logger
        self.logger.info("Initialisation of client %s" % self.name)
        self.debug = False                        # If we want sections with debug code to be executed
        self.host = 'localhost'                   # Remote host address (or ip) where to send files
        self.type = 'single-file'                 # Must be in ['single-file', 'bulletin-file', 'file', 'am', 'wmo', 'amis']
        self.protocol = None                      # First thing in the url: ftp, file, am, wmo, amis
        self.batch = 100                          # Number of files that will be read in each pass
        self.timeout = 10                         # Time we wait between each tentative to connect
        self.maxLength = 0                        # max Length of a message... limit use for segmentation, 0 means unused

        self.validation = True                    # Validation of the filename (prio + date)
        self.patternMatching = True               # Verification of the emask and imask of the client before sending a file
        self.cache = True                         # Check if the file has already been sent (md5sum present in the cache)
        self.mtime = 0                            # Integer indicating the number of seconds a file must not have
                                                  # been touched before being picked

        self.sorter = 'MultiKeysStringSorter'     # Class (or object) used to sort
        self.masks = []                           # All the masks (imask and emask)
        self.url = None
        self.collection = None                    # Client do not participate in the collection effort

        # Socket Attributes
        self.port = None 

        # Files Attributes
        self.user = None                    # User name used to connect
        self.passwd = None                  # Password 
        self.ftp_mode = 'passive'           # Default is 'passive', can be set to 'active'
        self.dir_mkdir = False              # Verification and creation of directory inside ftp...
        self.dir_pattern = False            # Verification of patterns in destination directory

        self.chmod = 666                    # when the file is delevered chmod it to this value
        self.timeout_send = 0               # Timeout in sec. to consider a send to hang ( 0 means inactive )
        self.lock = '.tmp'                  # file send with extension .tmp for lock
                                            # if lock == "umask" than use umask 777 to put files


        self.readConfig()
        #self.printInfos(self)

    def readConfig(self):
        
        def isTrue(s):
            if  s == 'True' or s == 'true' or s == 'yes' or s == 'on' or \
                s == 'Yes' or s == 'YES' or s == 'TRUE' or s == 'ON' or \
                s == '1' or  s == 'On' :
                return True
            else:
                return False

        def stringToOctal(string):
            if len(string) != 3:
                return 0644
            else:
                return int(string[0])*64 + int(string[1])*8 + int(string[2])

        currentDir = '.'                # Current directory
        currentFileOption = 'WHATFN'    # Under what filename the file will be sent (WHATFN, NONE, etc., See PDS)

        filePath = PXPaths.TX_CONF +  self.name + '.conf'
        #print filePath
        try:
            config = open(filePath, 'r')
        except:
            (type, value, tb) = sys.exc_info()
            print("Type: %s, Value: %s" % (type, value))
            return 

        for line in config.readlines():
            words = line.split()
            if (len(words) >= 2 and not re.compile('^[ \t]*#').search(line)):
                try:
                    if words[0] == 'imask': self.masks.append((words[1], currentDir, currentFileOption))  
                    elif words[0] == 'emask': self.masks.append((words[1],))
                    elif words[0] == 'directory': currentDir = words[1]
                    elif words[0] == 'filename': currentFileOption = words[1]
                    elif words[0] == 'destination':
                        self.url = words[1]
                        urlParser = URLParser(words[1])
                        (self.protocol, currentDir, self.user, self.passwd, self.host, self.port) =  urlParser.parse()
                        if len(words) > 2:
                            currentFileOption = words[2]
                    elif words[0] == 'validation': self.validation =  isTrue(words[1])
                    elif words[0] == 'cache': self.cache =  isTrue(words[1])
                    elif words[0] == 'patternMatching': self.patternMatching =  isTrue(words[1])
                    elif words[0] == 'mtime': self.mtime = int(words[1])
                    elif words[0] == 'sorter': self.sorter = words[1]
                    elif words[0] == 'type': self.type = words[1]
                    elif words[0] == 'protocol': self.protocol = words[1]
                    elif words[0] == 'maxLength': self.maxLength = int(words[1])
                    elif words[0] == 'host': self.host = words[1]
                    elif words[0] == 'user': self.user = words[1]
                    elif words[0] == 'password': self.passwd = words[1]
                    elif words[0] == 'batch': self.batch = int(words[1])
                    elif words[0] == 'debug' and isTrue(words[1]): self.debug = True
                    elif words[0] == 'timeout': self.timeout = int(words[1])
                    elif words[0] == 'chmod': self.chmod = stringToOctal(words[1])
                    elif words[0] == 'timeout_send': self.timeout_send = int(words[1])
                    elif words[0] == 'lock': self.lock = words[1]
                    elif words[0] == 'ftp_mode': self.ftp_mode = words[1]
                    elif words[0] == 'dir_pattern': self.dir_pattern =  isTrue(words[1])
                    elif words[0] == 'dir_mkdir': self.dir_mkdir =  isTrue(words[1])
                except:
                    self.logger.error("Problem with this line (%s) in configuration file of client %s" % (words, self.name))

        if not self.validation:
            self.sorter = 'None'    # Must be a string because eval will be subsequently applied to this

        config.close()
    
        #self.logger.debug("Configuration file of client %s has been read" % (self.name))

    def _getMatchingMask(self, filename): 
        for mask in self.masks:
            if fnmatch.fnmatch(filename, mask[0]):
                try:
                    if mask[2]:
                        return mask
                except:
                    return None
        return None

    def getDestInfos(self, filename):
        """
        WHATFN         -- First part (':') of filename 
        HEADFN         -- Use first 2 fields of filename
        NONE           -- Use the entire filename
        TIME or TIME:  -- TIME stamp appended
        DESTFN=fname   -- Change the filename to fname

        ex: mask[2] = 'NONE:TIME'
        """
        mask = self._getMatchingMask(filename)
        if mask:
            timeSuffix = ''
            firstPart = filename.split(':')[0]
            destFileName = filename
            for spec in mask[2].split(':'):
                if spec == 'WHATFN':
                    destFileName =  firstPart
                elif spec == 'HEADFN':
                    headParts = firstPart.split('_')
                    if len(headParts) >= 2:
                        destFileName = headParts[0] + '_' + headParts[1] 
                    else:
                        destFileName = headParts[0] 
                elif spec == 'NONE':
                    destFileName =  filename
                elif re.compile('DESTFN=.*').match(spec):
                    destFileName = spec[7:]
                elif spec == 'TIME':
                    timeSuffix = ':' + time.strftime("%Y%m%d%H%M%S", time.gmtime())
                else:
                    self.logger.error("Don't understand this DESTFN parameter: %s" % spec)
                    return (None, None) 
            return (destFileName + timeSuffix, mask[1])
        else:
            return (None, None) 

    def printInfos(self, client):
        print("==========================================================================")
        print("Name: %s " % client.name)
        print("Host: %s" % client.host)
        print("Type: %s" % client.type)
        print("Protocol: %s" % client.protocol)
        print("Batch: %s" %  client.batch)
        print("Max length: %i" % client.maxLength)
        print("Mtime: %i" % client.mtime)
        print("Timeout: %s" % client.timeout)
        print("Sorter: %s" % client.sorter)
        print("URL: %s" % client.url)
        print("Port: %s" % client.port)
        print("User: %s" % client.user)
        print("Passwd: %s" % client.passwd)
        print("Chmod: %s" % client.chmod)
        print("Timeout_send: %i" % client.timeout_send)
        print("Lock: %s" % client.lock)
        print("FTP Mode: %s" % client.ftp_mode)
        print("DIR Pattern: %s" % client.dir_pattern)
        print("DIR Mkdir  : %s" % client.dir_mkdir)
        print("Validation: %s" % client.validation)
        print("Pattern Matching: %s" % client.patternMatching)
        print("Cache used: %s" % client.cache)

        print("******************************************")
        print("*       Client Masks                     *")
        print("******************************************")

        for mask in self.masks:
            print mask
        print("==========================================================================")

if __name__ == '__main__':

    client =  Client('wxo-b1')
    #client.readConfig()
    #client.printInfos(client)
    print client.getDestInfos('AWCNALO:TUTU:TITI:TOTO:MIMI:Directi')
    print client.getDestInfos('FPCN_DAN_MAN_lkdslfk:TUTU:TITI:TOTO:MIMI:Directi')
    print client.getDestInfos('WLCN_MAN_lkdslfk:TUTU:TITI:TOTO:MIMI:Direct')
    print client.getDestInfos('SMALLO:TUTU:TITI:TOTO:MIMI:Direct')
    print client.getDestInfos('WTCNALLO:TUTU:TITI:TOTO:MIMI:Direct')

    """
    for filename in os.listdir(PXPaths.TX_CONF):
        if filename[-5:] != '.conf': 
            continue
        else:
            client = Client(filename[0:-5])
            client.readConfig()
            client.printInfos(client)

    """

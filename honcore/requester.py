import hashlib, urllib2
from exceptions import *
from httplib import BadStatusLine


""" 
Sends requests to the HoN master servers.
These are just basic HTTP get requests which return serialised php.

A version of '2.1.0' forced the connection to be dropped by the server, changing it back to a 4 'digit' version fixes. Guess the version string
must be 4 digits..

TODO:
     * If sending a logout request times out then it's a bit... confusing as to what's going on. Could need cleaning up.

"""
_config_defaults = {
    "masterserver" : "http://masterserver.hon.s2games.com/", 
    "basicserver" : "http://heroesofnewerth.com/", 
    "version": "2.1.10.0"
}

class Requester:
    def __init__(self):
        self.config = _config_defaults

    def httpget(self, base, url):
        url = base + url
        header = { 'User-Agent' : "S2 Games/Heroes of Newerth/%s/lac/x86-biarch" % self.config["version"]}
        req = urllib2.Request(url, None, header)
        try:
            response = urllib2.urlopen(req, timeout=20)
            return response.read()
        except urllib2.HTTPError, e:
            # TODO : Find out what errors to catch.
            print e.code
            print e.read()
            raise MasterServerError(107)
        except urllib2.URLError, e:
            code = e.reason[0]
            if code == 104: # Connection reset by peer
                raise MasterServerError(110)
            elif code == 111:
                raise MasterServerError(111)
            elif code == "timed out":
                raise MasterServerError(112)
            elif code == -5:
                raise MasterServerError(114)
            else:
                print e
                print code
                raise MasterServerError(107)
        except BadStatusLine, e:
            raise MasterServerError(109, e)

    def httpost(self, url):
        """ WHY """
        pass

    def login(self, username, password):
        """ Requests basic information about the user's account """
        url = "client_requester.php?f=auth&login=%s&password=%s" % (username, password)
        return self.httpget(self.config['masterserver'], url)

    def logout(self, cookie):
        """ 
        Sends a logout 'request'. 
        Returns a:2:{i:0;b:1;s:12:"client_disco";s:2:"OK";} on a successful logout.
        """
        url = "client_requester.php?f=logout&cookie=%s" % cookie 
        return self.httpget(self.config['masterserver'], url)

    def motd(self):
        """ Requests the message of the day list from the server.
            Contains the last 6 message of the day(s??) Messages of the day?.
        """
        url = "/gen/client_motd3.php?data=retrieve"
        return self.httpget(self.config['basicserver'], url) 
        
    def server_list(self, cookie, gametype):
        pass

    def nick2id(self, nickname):
        pass

    def new_buddy(self, cookie, aid, bid):
        pass

    def remove_buddy(self, cookie, aid, bid):
        pass

    def new_banned(self, cookie, aid, bid, reason):
        pass

    def remove_banned(self, cookie, aid, bid, reason):
        pass

    def new_ignored(self, cookie, aid, iid, reason):
        pass

    def remove_ignored(self, cookie, aid, iid, reason):
        pass

    def stats_request(self, aid):
        pass

    def stats_request_ranked(self, aid):
        pass

    def patcher(self, version, os, arch):
        pass

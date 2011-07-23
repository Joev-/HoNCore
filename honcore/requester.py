import hashlib, urllib2
from exceptions import *
from httplib import BadStatusLine

config = {
	"masterserver" : "http://masterserver.hon.s2games.com/", 
	"basicserver" : "http://heroesofnewerth.com/", 
	"honver" : "2.0.40.2"
}

header = { 'User-Agent' : "S2 Games/Heroes of Newerth/" + config['honver'] + "/lac/x86-biarch" }

""" 
Sends requests to the HoN master servers.
These are just basic HTTP get requests which return serialised php.

TODO:
	 * If sending a logout request times out then it's a bit... confusing as to what's going on. Could need cleaning up.

"""

def httpget(base, url):
	url = base + url
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
		else:
			print e
			print code
			raise MasterServerError(107)
	except BadStatusLine, e:
		raise MasterServerError(109, e)

def httpost(url):
	""" When should POST be used VS GET?"""
	pass

def login(username, password):
	""" Requests basic information about the user's account """
	url = "client_requester.php?f=auth&login=%s&password=%s" % (username, password)
	return httpget(config['masterserver'], url)

def logout(cookie):
	""" 
	Sends a logout 'request'. 
	Returns a:2:{i:0;b:1;s:12:"client_disco";s:2:"OK";} on a successful logout.
	"""
	url = "client_requester.php?f=logout&cookie=%s" % cookie 
	return httpget(config['masterserver'], url)

def motd():
	""" Requests the message of the day list from the server.
		Contains the last 6 message of the day(s??) Messages of the day?.
	"""
	url = "/gen/client_motd2.php?data=retrieve"
	return httpget(config['basicserver'], url) 
	
def server_list(cookie, gametype):
	pass

def nick2id(nickname):
	pass

def new_buddy(cookie, aid, bid):
	pass

def remove_buddy(cookie, aid, bid):
	pass

def new_banned(cookie, aid, bid, reason):
	pass

def remove_banned(cookie, aid, bid, reason):
	pass

def new_ignored(cookie, aid, iid, reason):
	pass

def remove_ignored(cookie, aid, iid, reason):
	pass

def stats_request(aid):
	pass

def stats_request_ranked(aid):
	pass

def patcher(version, os, arch):
	pass
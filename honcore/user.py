from exceptions import *

""" 
Functions and information for globally accessable objects, Users, Account, Channels, Buddies/Bans/Ignores. etc.
These are needed as they are global objects which are created when a response is returned from the client requester 
and will be updated in real time. The response contains a big list of buddies, bans, ignores, and other than watching for
buddy/ignore/ban add/remove packets is the only way to obtain this initial information.
"""
account = None

""" Functions """
def id2nick(bid):
	""" Provide a user's nick instead of their ID. Purely visual, useful for notifications.
		TODO: Modify so it can find either a buddy or clan member.
	"""
	for user in account.buddy_list:
		if bid == user.buddy_id:
			if user.clantag != "":
				clantag = "[" + user.clantag + "]"
			else:
				clantag = ""
			name = clantag + user.nickname
			return name
	return ""

def set_status(nick, server, gamename, status):
	""" Update the status for a buddy.
		Some data like server and game name are not stored... Buuuut, they could be.
	"""
	global account
	for user in account.buddy_list:
		if user.nickname == nick:
			user.status = status

def get_buddy_list():
	return account.buddylist

"""
A User object holds information pertaining a user, can be a clan member, a buddy, both, or none. 

A user holds the following
	+ accId			~ The user's account id.
	+ nick 			~ The user's nickname.
	+ accIcon		~ The user's account icon. e.g. ....
	+ clanTag 		~ The user's clan tag, to go together with the nick.
	+ status		~ The current status of the user. e.g. Not Found, Offline, In Channels... and In Game....
	+ flags			~ Flags for the user, e.g. prepurchased, officer, admin, staff.

Possible information to hold.
	+ If the user is in a game it would show the game name and server that they are in. 
	  Storing it would reduce requests, and it would be changed when the user leaves a game since a new
	  status is sent anyway.

Some information about users can be obtained using a whois command, the whois returns the user's status and the channels the 
user is currently in unless the user is in a game. If the user is in a game then it returns the game name and the... current
game time. e.g. "Current game time: Lobby" or "Current game time: Banning" or "Current game time: 0:39:00."
"""
class User:
	def __init__(self, accid, nick, buddy_id=None, clan_id=None, clan_tag="", clan_name=None, status=0, flag=0x00):
		self.account_id = account_id
		self.nickname = nick
		self.buddy_id = buddy_id
		self.clan_id = clan_id
		self.clan_tag = clan_tag
		self.clan_name = clan_name
		self.status = status
		self.flag = flag

"""
An account object holds information pertaining to the user who is logged in. It will store some account information 
which may be needed by the program. For security it should not store the password (Plus it's not needed anyway..).

What is the super_id used for, and what is the different between the super_id and account_id. Possibly the super_id is the main account
and if a sub account is purchased it is used to link to the main account? If that is the case the account_id MUST be used when performing actions. The 
super_id should only be used when a reference to the main account is needed. TODO: Find out what these are (e.g. shop stuff I guess)

"""
class Account:
	def __init__(self, super_id, account_id, nickname, cookie, auth_hash, chat_url, ip):
		self.super_id = super_id
		self.account_id = account_id
		self.nickname = nickname
		self.cookie = cookie
		self.auth_hash = auth_hash
		self.chat_url = chat_url
		self.ip = ip
		# self.contacts = []
		self.buddy_list = {}
		self.ban_list = {}
		self.ignore_list = {}
		self.logged_in = False

		global account
		account = self
""" 
Channel Information

Needs work and more information.

A channel holds the following
	+ id		~ The id of the channel
	+ name		~ The name of the channel
"""

class Channel:
	pass

		

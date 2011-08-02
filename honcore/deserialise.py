import user
from exceptions import *

from lib import phpserialize as phpd

""" Deserialises the php stuff and creates objects, not really... big... since there's this like, library... already.. """

""" 
There seems to be a difference between super_id and account_id, atleast in a trial account. 
A trial account that I created would not be able to use this program as the super_id was
different to the account id. Replacing super_id with account_id is the fix, but as to why
is a case to be solved.

If a user does not have any buddies then the buddy array is structured as follows.

buddy {
	error {
		"No buddies found" 
	}
}

If a user has a buddy then it is structured as the following.

buddy_list {
	<account_id> {
		<buddy_data_array>
	}
}

"""

def parse_raw(raw):
	""" Takes raw serialised data and returns raw non-serialised data """
	return phpd.loads(raw)

def parse(raw):
	data = phpd.loads(raw)
	
	if 'auth' in data:
		raise MasterServerError(102)
	
	get_basic_info(data)

	try:
		get_buddies(data['buddy_list'])
	except KeyError:
		user.account.buddy_list = {}
	
	try:
		get_banned_list(data['banned_list'])
	except KeyError:
		user.account.ban_list = {}

	try:
		get_ignore_list(data['ignored_list'])
	except KeyError:
		user.account.ignore_list = {}
	
	try:
		get_clan_memebrs(data['clan_member_info'])
	except KeyError:
		# raise MasterServerError(123)
		pass

	return True

def get_basic_info(data):
	try:
		user.account = user.Account(int(data['super_id']), int(data['account_id']), data['nickname'], data['cookie'], data['auth_hash'], data['chat_url'], data['ip'])
	except KeyError, e:
		raise MasterServerError(101, "KeyError", e)
	
def get_buddies(buddylist):
	""" NOTE: It is not possible to get flag and status here. """
	for userKey in buddylist:
		accid = buddylist[userKey]['account_id']
		buddyid = buddylist[userKey]['buddy_id']
		nick = buddylist[userKey]['nickname']
		clantag = buddylist[userKey]['clan_tag'] or ""
		clanname = buddylist[userKey]['clan_name']

		buddy = user.User(accid, nick, buddy_id=buddyid, clan_tag=clantag, clan_name=clanname, status=0, flag=0)
		user.account.buddy_list[accid] = buddy

def get_banned_list(data):
	pass

def get_ignore_list(data):
	pass

def get_clan_memebrs(data):
	pass
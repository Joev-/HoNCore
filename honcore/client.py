import sys, struct, socket, time
import requester, packet, deserialise, user
from exceptions import *

connection = { "socket" : None, "connected" : False }
config = {"chatport" : 11031,"chatver" : 0x0F,"invis" : False}

# TODO: Put to use? Maybe make a utils module and provide motd_to_html()
color_map = ["00","1C","38","54","70","8C","A8","C4","E0","FF"]

def configure(*args, **kwargs):
	config_map = {
		"chatport" : config,
		"chatver" : config,
		"invis" : config,
		"masterserver" : requester.config,
		"basicserver" : requester.config,
		"honver" : requester.config
	}
	
	for kwarg in kwargs:
		if kwarg in config_map:
			config_map[kwarg][kwarg] = kwargs[kwarg]

""" Account related functions
	* login
	* logout
"""
def login(username, password):
	""" HTTP login request.
		Catches the following:
			* Failed to get login data after 3 attempts.
			* Could not connect to the masterserver.
			* Could not obtain login data
			* Incorrect username/password
		TODO:	Handle HTTP errors here somewhere.
				Some can be handled easily with a retry, but if an error shows that the server will never 
				accept a connection in the near future then it should stop trying to connect.
	"""

	attempts = 1
	while True:
		try:
			response = requester.login(username, password)
			break
		except MasterServerError:
			if attempts == 3:
				raise	# Re-raise the last exception given
			timeout = pow(2, attempts)
			time.sleep(timeout)
			attempts += 1

	if response == None:
		raise MasterServerError(100)
	elif response == "":
		raise MasterServerError(101)

	# Pass the data to the deserialiser
	try:
		deserialise.parse(response)
		user.account.logged_in = True
	except MasterServerError:
		raise MasterServerError(101)

def logout():
	""" Send a logout request to the masterserver and log out the account.
		Is forcing the logout okay? Breaking the connection to the chat server technically 
		logs the user out... What is the effect of sending the logout request to the masterserver?
		TODO: Fail cases, handle them!
			* Connection timed out
			* Connection refused.
	"""
	if user.account == None:
		return
	
	if not user.account.cookie:
		user.account.logged_in = False
	else:
		attempts = 3
		while True:
			try:
				requester.logout(user.account.cookie)
				user.account.logged_in = False
				break
			except MasterServerError, e:
				if attempts == 3:
					raise	# Re-raise the last exception given
				timeout = pow(2, attempts)
				time.sleep(timeout)
				attempts += 1


def is_logged_in():
	if user.account == None: return False
	return user.account.logged_in


""" Chatserver related functions"""
def chat_connect():
	""" Creates a socket and sends the initial authentication request to the chatserver.
		Catches the following:
			* The server responded to the authentication request.
			* The server did not respond to the authentication request.
			* Account data mismatch.
			* Connection to the server timed out.
	"""
	if user.account == None or user.account.cookie == None or user.account.auth_hash == None:
		raise ChatServerError(205)
	
	global connection
	socket.setdefaulttimeout(61)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		s.connect((user.account.chat_url, config['chatport']))
		print "Opened socket on %s:%s" % (user.account.chat_url, config['chatport'])
	except socket.timeout:
		raise ChatServerError(201)

	# Send initial authentication request to the chat server.
	# If the chat server did not respond to the auth request then increment the chatver.
	attempts = 1
	while True:
		try:
			packet.send_auth(s, user.account.account_id, user.account.cookie, user.account.ip, user.account.auth_hash, config['chatver'], config['invis'])
			break
		except ChatServerError, e:
			if attempts == 3:
				connection['connected'] = False # Make sure this is set.
				if e.code == 206: # Broken Pipe, want to see the message because it's important!
					raise
				else:
					raise ChatServerError(203)
			timeout = pow(2, attempts)
			time.sleep(timeout)
			attempts += 1
		
	connection['connected'] = True
	connection['socket'] = s

	# Start listening for packets from the chat server.
	listener = packet.Listener(connection)
	listener.daemon = True
	listener.start()


def chat_disconnect():
	""" Disconnect gracefully from the chat server and close and remove the socket."""
	s = connection['socket']
	if s:
		connection['connected'] = False # Safer to stop the thread with this first.
		s.shutdown(socket.SHUT_RDWR)
		s.close()
		connection['socket'] = None

def is_connected():
	""" Test for chat server connection """
	return connection['connected']

""" Message of the day related functions"""

def motd_get():
	""" 
	Requests the message of the day entries from the server and then pushes them through motd_parse.
	Returns a dict of motd entries.
	"""
	raw = requester.motd()
	try:
		raw = deserialise.parse_raw(raw)['data']
	except ValueError:
		raise MasterServerError(108)
	return motd_parse(raw)

def motd_parse(raw):
	""" 
	Parses the message of the day entries into a dictionary of the format:
	motd_list = [
		{
			["title"] = "Item 1 title",
			["author"] = "MsPudding",
			["date"] = "6/30/2011"
			["body"] = "This is the body of the message including line\n feeds"
		},
		{
			["title"] = "Item 2 title", 
			["author"] = "Konrar",
			["date"] = "6/29/2011",
			["body"] = "This is the body text\n Sometimes there are ^rColours^*"
		}
	]
	The first index will always be the newest....... Right?
	"""
	# Split the full string into a list of entries.
	motd_list = []
	entries = raw.split("|")
	for entry in entries:
		title, body, author, date = entry.split("`")
		motd_list.append({"title" : title, "author" : author, "date" : date, "body" : body})
	return motd_list

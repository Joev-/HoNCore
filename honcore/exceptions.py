"""
Custom exceptions to be raised by this library and caught by any program using this library.
Helps debug login/logout events/incorrect data and socket errors (timeout, broken pipes etc).

TODO	 
	 * urllib2 sometimes throws BadStatusLine which means the server responded with an unknown HTTP status code. 
	   Needs to be handled correctly, it should throw a MasterServerError 109, but it needs a stronger definition.
"""

class HoNException(Exception):
	"""
	Base exception for all exceptions for this library.
	Used when there's not a specific exception to catch.
	"""
	def __init__(self, code, *args):
		self.code = code
		self.error = errormap[code]
	
	def __str__(self):
		return repr("Error %d: %s" % (self.code, self.error))

class HoNConfigError(HoNException):
	"""
	Exception relating to the configuration data.
	Can be raised if the configuration passed does not satisfy the requirements.
	"""
	
class MasterServerError(HoNException):
	"""
	Exception related to the master server. 
	Can be raised if invalid data is returned or if the connection times out.

	"""

class ChatServerError(HoNException):
	"""
	Ecxception related to the chat server.
	Can be raised if invalid data is received or if the socket times out and the
	connection to the server is lost.

	"""

errormap = {
	100 : 'Could not connect to the masterserver.',
	101 : 'Could not obtain login data.',
	102 : 'Incorrect username/password.',
	103 : 'Failed to get login data after 3 attempts.',
	104 : 'Connection to the master server timed out.',
	105 : 'Connection to the master server was rejected.',
	106 : 'Master server failed to receieve logout request, forcing logout.',
	107 : 'Requester HTTP error.', # Don't leave this in, expand it to handle each different HTTP/URL Error.
	108 : 'Unexpected opcode when parsing PHP serialisation.',
	109 : 'Bad HTTP status code.',
	110 : 'Connection reset by peer', # Good sign it's down, it's dropping connections?
	111 : 'Connection refused', # Very good sign it's down, it's refusing connections?
	112 : 'Connection timed out',
	120 : 'No buddies found',
	121 : 'No ban list found',
	122 : 'No ignored users found',
	123 : 'No clan members found',
	200 : 'Chat server did not respond to authentication request.',
	201 : 'Connection to the chat server timed out.',
	202 : 'Connection to the chat server was rejected.',
	203 : 'Failed to connect to the chat server after 3 attempts.',
	204 : 'Empty packet received.',
	205 : 'No cookie/auth hash provided.',
	206 : 'Broken Pipe, is the chat version correct?',
}
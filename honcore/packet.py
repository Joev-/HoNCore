import struct, time, threading, socket
import client, handler
from exceptions import *
from packetdef import *
from lib.construct import *

HON_FLAGS_NONE			= 0x00
HON_FLAGS_OFFICER		= 0x01
HON_FLAGS_LEADER		= 0x02
HON_FLAGS_ADMINISTRATOR	= 0x03
HON_FLAGS_STAFF			= 0x04
HON_FLAGS_PREPURCHASED	= 0x40

HON_STATUS_OFFLINE		= 0
HON_STATUS_ONLINE		= 3
HON_STATUS_INLOBBY		= 4
HON_STATUS_INGAME		= 5

HON_MODE_NORMAL			= 0x00
HON_MODE_INVISIBLE		= 0x03

HON_NOTIFICATION_ADDED_AS_BUDDY   =	0x01
HON_NOTIFICATION_BUDDY_ACCEPTED   =	0x02
HON_NOTIFICATION_REMOVED_AS_BUDDY =	0x03
HON_NOTIFICATION_BUDDY_REMOVED    =	0x04

class Listener(threading.Thread):
	""" 
	Listener class, listens on a socker for packets, sends those packets to
	the packet parser, which then feeds the packet into any registered event
	and packet handlers.
	"""
	def __init__(self, conn):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.conn = conn
		self.socket = conn['socket']
	
	def run(self):
		try:
			while self.conn['connected'] == True:
				packet = self.socket.recv(512)
				parse(packet)
			
			self.stop()
		except socket.timeout:
			raise ChatServerError(201)
	
	def stop(self):
		self._stop.set()

def parse(packet):
	"""
	Extracts the packet ID and then pushes the packet through to a matching registered packet handler,
	this handler then extracts any useful data into a dict of kwargs which can then be handed to any matching
	registered event handler.

	TODO: Set up a method of handling oversized packets, this needs to compared the packet size
		  given in the first 2 bytes with the amount of data received on the socket, if the sizes do not
		  match then subtract the amount received from the total expected size and tell the socket to recv
		  that new amount. This all needs to be done before passing the packet to the packet parser.

	"""
	if len(packet) == 0:
		# What should be done here?
		# raise ChatServerError(204)
		return
	
	packet_id = struct.unpack('H', packet[2:4])[0]

	# For debugging, possible to remove/leave it and expand on it?
	if 'all' in handler.events:
		handler.events['all'](packet_id=packet_id, packet=packet)
	
	""" Passes the packet to a packet handler so it can be parsed for data. The returned data
		is then passed to each event handler that requests it as a list of named keywords which
		are taken as arguments.
	"""
	if packet_id in handler.packets:
		kwargs = handler.packets[packet_id](packet)
		if packet_id in socket_events:
			for event, func in handler.events.items():
				if socket_events[packet_id] == event:
					num_args = func.func_code.co_argcount
					func(**kwargs) if num_args > 0 else func()
	else:
		# Unknown packet, raise a debug message somehow.
		pass

def send_auth(sock, account_id, cookie, ip, auth_hash, chatver, invis):
	""" Sends the initial authentication packet to the chat server and parses the 
		response returned by the server.
	"""

	c = Struct("login",
		ULInt16("id"),
		ULInt32("aid"),
		String("cookie", len(cookie)+1, encoding="utf8", padchar = "\x00"),
		String("ip", len(ip)+1, encoding="utf8", padchar = "\x00"),
		String("auth", len(auth_hash)+1, encoding="utf8", padchar = "\x00"),
		ULInt32("proto"),
		ULInt8("unknown"),
		ULInt32("mode")
	)

	packet = c.build(Container(id=HON_CS_AUTH_INFO, aid=account_id, cookie=unicode(cookie), ip=unicode(ip), 
							auth=unicode(auth_hash), proto=chatver, unknown=0x01, mode=0x03 if invis else 0x00))
	
	sock.send(packet)

	resp = sock.recv(256)
	if len(resp) == 0:
		raise ChatServerError(204)
	
	# Check that the server sends the acknowledgement. 
	if struct.unpack('H', resp[2:4])[0] != HON_SC_AUTH_ACCEPTED:
		raise ChatServerError(200)


""" Packet Handlers.
	In numeric order.
	Incoming packets.
	<--- HON_SC_PING
	<--- HON_SC_TOTAL_ONLINE
"""

@handler.packet(HON_SC_INITIAL_STATUS)
def parse_initial_status(packet):
	""" 
	The initial status packet contains a of a lot of information which can be used to set
	the initial state of buddies and servers and players online and what not.
	"""
	pass

@handler.packet(HON_SC_PING)
def parse_ping(packet):
	""" Replies to a ping request (0x2A00) with a pong response (0x2A01) """
	s = client.connection['socket']
	s.send(struct.pack('H', HON_CS_PONG))
	return {}

@handler.packet(HON_SC_TOTAL_ONLINE)
def parse_total_online(packet):
	""" Gets the number of players online """
	count = struct.unpack('I', packet[4:8])[0]
	return {'players_online' : count}


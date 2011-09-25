import sys, struct, time, threading, socket
import handler, user
from exceptions import *
from packetdef import *
from lib.construct import *

HON_FLAGS_NONE          = 0x00
HON_FLAGS_OFFICER       = 0x01
HON_FLAGS_LEADER        = 0x02
HON_FLAGS_ADMINISTRATOR = 0x03
HON_FLAGS_STAFF         = 0x04
HON_FLAGS_PREPURCHASED  = 0x40

HON_STATUS_OFFLINE      = 0
HON_STATUS_ONLINE       = 3
HON_STATUS_INLOBBY      = 4
HON_STATUS_INGAME       = 5

HON_MODE_NORMAL         = 0x00
HON_MODE_INVISIBLE      = 0x03

HON_NOTIFICATION_ADDED_AS_BUDDY   = 0x01
HON_NOTIFICATION_BUDDY_ACCEPTED   = 0x02
HON_NOTIFICATION_REMOVED_AS_BUDDY = 0x03
HON_NOTIFICATION_BUDDY_REMOVED    = 0x04

class SocketListener(threading.Thread):
    """ 
    Listener class, listens on a socker for packets, sends those packets to
    the packet parser, which then feeds the packet into any registered event
    and packet handlers.
    """
    def __init__(self, chat_socket):
        threading.Thread.__init__(self)
        self._stop = threading.Event()
        self.chat_socket = chat_socket
        self.socket = chat_socket.socket
    
    def run(self):
        while self.chat_socket.is_connected:
            try:
                packet = self.socket.recv(512)
                if not packet:
                    break
                self.parse(packet)
                time.sleep(1)
            except socket.timeout:
                break
            except socket.error:
                break
        self.chat_socket.connected = False
        self.stop()

    def stop(self):
        self._stop.set()

    def parse(self, packet):
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
            kwargs = handler.packets[packet_id](self.chat_socket, packet)
            if packet_id in socket_events:
                for event, func in handler.events.items():
                    if socket_events[packet_id] == event:
                        num_args = func.func_code.co_argcount
                        func(**kwargs) if num_args > 0 else func()
        else:
            # Unknown packet, raise a debug message somehow.
            pass

class ChatSocket:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(60)
        self.connected = False

    def connect(self, chat_url, chat_port):
        """ 
        Opens a socket connection to the url and port provided from the authentication
        server.
        """
        try:
            self.socket.connect((chat_url, chat_port))
        except socket.timeout:
            raise HoNCoreError(11) # Socket timed out
        except socket.error, e:
            if e.errno == 110:
                raise HoNCoreError(11) # Socket timed out
            raise HoNCoreError(10) # Socket error
    
    def disconnect(self):
        """ Disconnect gracefully from the socket and close the socket down. """
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error:
            raise HoNCoreError(10)
        self.connected = False

    @property
    def is_connected(self):        
        return self.connected

    def get_local_port(self):
        addr, port = self.socket.getsockname()
        return port 

    def send_auth(self, account_id, cookie, ip, auth_hash, chatver, invis):
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
        
        # print "Sending packet - 0x%x:%s:%s:%s:%s:0x%x:0x%x:0x%x" % (HON_CS_AUTH_INFO, account_id, cookie, ip, auth_hash, chatver, 0x01, 0x00)
        try:
            self.socket.send(packet)
        except socket.error, e:
            if e.errno == 32:
                raise ChatServerError(206)

        resp = self.socket.recv(256)
        if len(resp) == 0:
            raise ChatServerError(204)
        
        # Check that the server sends the acknowledgement. 
        if struct.unpack('H', resp[2:4])[0] != HON_SC_AUTH_ACCEPTED:
            raise ChatServerError(200)


    """ Packet Handlers."""

    @handler.packet_handler(HON_SC_INITIAL_STATUS)
    def parse_initial_status(self, packet):
        """ 
        The initial status packet contains information for all available buddy and clan members, 
        as well as some server statuses and matchmaking settings.
        """
        contact_count = int(struct.unpack_from('I', packet[4:8])[0]) # Tuples?!!
        contact_data = packet[8:]
        if contact_count > 0:
            i = 1
            print("Parsing data for %i contacts." % contact_count)
            while i <= int(contact_count):
                status = int(struct.unpack_from('B', contact_data[4])[0])
                nick = ""
                gamename = ""
                flag = ""
                if status == HON_STATUS_INLOBBY or status == HON_STATUS_INGAME:
                    c = Struct("buddy", ULInt32("buddyid"), Byte("status"), Byte("flag"), CString("server"), CString("gamename"))
                    r = c.parse(contact_data)
                    nick = user.id2nick(r.buddyid)
                    flag = str(r.flag)
                    contact_data = contact_data[6 + (len(r.server)+1+len(r.gamename)+1):]
                    gamename = r.gamename
                else:
                    c = Struct("buddy", ULInt32("buddyid"), Byte("status"), Byte("flag"))
                    r = c.parse(contact_data[:6])
                    nick = user.id2nick(r.buddyid)
                    flag = str(r.flag)
                    contact_data = contact_data[6:]
                
                if nick != "":
                    # Check for a name because sometimes my own account id is in the list of online buddies, why?
                    # Above message is no longer valid, and this should be revised, the logged in user's name is in the list whenever they
                    # are in a clan because this user data contains data for clan members and buddies.
                    # user.updateStatus(nick)
                    if gamename is not "":
                        print(nick + " is online and in the game " + gamename)
                    else:
                        print(nick + " is online.")
                i+=1

    @handler.packet_handler(HON_SC_PING)
    def parse_ping(self, socket):
        """ Replies to a ping request (0x2A00) with a pong response (0x2A01) """
        self.socket.send(struct.pack('H', HON_CS_PONG))
        return {}

    @handler.packet_handler(HON_SC_TOTAL_ONLINE)
    def parse_total_online(self, packet):
        """ Gets the number of players online """
        count = struct.unpack('I', packet[4:8])[0]
        return {'players_online' : count}

    @handler.packet_handler(HON_SC_WHISPER)
    def parse_whisper(self, packet):
        """ A normal whisper from anyone """
        print "Parsing whisper"
        c = Struct("packet", ULInt16("size"), ULInt16("packetid"), CString("name"), CString("message"))
        r = c.parse(packet)
        return {"name" : r.name, "message" : r.message }

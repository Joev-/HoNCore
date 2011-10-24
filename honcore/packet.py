import sys, struct, time, threading, socket
import handler, user
from exceptions import *
from packetdef import *
from lib.construct import *

""" TODO: Update constants """
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
    Listener class, listens on a socket for packets, ensures they are valid
    and then sends the packets off to be parsed.
    """
    def __init__(self, chat_socket):
        threading.Thread.__init__(self)
        self.chat_socket = chat_socket
        self.socket = chat_socket.socket
    
    def run(self):
        while self.chat_socket.is_connected:
            try:
                packet = self.socket.recv(512)
                if not packet:
                    break
                self.chat_socket.parse_packet(packet)
                time.sleep(1)
            except socket.timeout:
                break
            except socket.error:
                break

class ChatSocket:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(60)
        self.connected = False
        self.packet_parser = PacketParser()
        self.events = {}

        self.__create_events()

    def __create_events(self):
        """ Create each event that can be triggered by the client. """
        self.events[HON_SC_AUTH_ACCEPTED] = Event("Auth Accepted", HON_SC_AUTH_ACCEPTED)
        self.events[HON_SC_PING] = Event("Ping", HON_SC_PING)
        self.events[HON_SC_CHANNEL_MSG] = Event("Channel Message", HON_SC_CHANNEL_MSG)
        self.events[HON_SC_CHANGED_CHANNEL] = Event("Changed Channel", HON_SC_CHANGED_CHANNEL)
        self.events[HON_SC_JOINED_CHANNEL] = Event("Joined Channel", HON_SC_JOINED_CHANNEL)
        self.events[HON_SC_LEFT_CHANNEL] = Event("Left Channel", HON_SC_LEFT_CHANNEL)
        self.events[HON_SC_WHISPER] = Event("Whisper", HON_SC_WHISPER)
    
        self.events[HON_SC_TOTAL_ONLINE] = Event("Total Online", HON_SC_TOTAL_ONLINE)

        # Transparently connect the ping event to the pong sender.
        self.events[HON_SC_PING].connect(self.send_pong)

    @property
    def is_connected(self):        
        return self.connected
    
    @property
    def local_port(self):
        addr, port = self.socket.getsockname()
        return port

    def connect(self, chat_url, chat_port):
        """ Opens a socket connection to the url and port provided from the authentication server. """
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

    def parse_packet(self, packet):
        """ Core function to tie together all of the packet parsing. """
        packet_id = self.packet_parser.parse_id(packet)
            
        try:
            packet_data = self.packet_parser.parse_data(packet_id, packet)
        except HoNCoreError, e:
            if e.code == 12: # Unknown packet received.    
                return False

        if packet_id in self.events:
            event = self.events[packet_id]
            event.trigger(**packet_data)
    
    def send_pong(self):
        self.socket.send(struct.pack('H', HON_CS_PONG))

    def send_channel_message(self):
        pass
    
    def send_whisper(self):
        pass
    
    def send_auth_info(self, account_id, cookie, ip, auth_hash, protocol, invis):
        """ 
        Sends the initial authentication packet to the chat server and parses the 
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
                                auth=unicode(auth_hash), proto=protocol, unknown=0x01, mode=0x03 if invis else 0x00))
        
        # print "Sending packet - 0x%x:%s:%s:%s:%s:0x%x:0x%x:0x%x" % (HON_CS_AUTH_INFO, account_id, cookie, ip, auth_hash, protocol, 0x01, 0x00)
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
    
    def send_buddy_add_notify(self):
        pass

    def send_join_game(self):
        pass
    
    def send_clan_message(self):
        pass

    def send_private_message(self):
        pass

    def send_join_channel(self):
        pass

    def send_whisper_buddies(self):
        pass

    def send_leave_channel(self):
        pass

    def send_user_info(self):
        pass

    def send_update_topic(self):
        pass

    def send_channel_kick(self):
        pass

    def send_channel_ban(self):
        pass
    
    def send_channel_unban(self):
        pass

    def send_channel_silence_user(self):
        pass

    def send_channel_promote(self):
        pass

    def send_channeL_demote(self):
        pass

    def send_channel_auth_enable(self):
        pass

    def send_channel_auth_disable(self):
        pass

    def send_channel_auth_add(self):
        pass

    def send_channel_auth_delete(self):
        pass

    def send_channel_auth_list(self):
        pass

    def send_join_channel_password(self):
        pass

    def send_clan_add_member(self):
        pass

    def send_channel_emote(self):
        pass

    def send_buddy_accept(self):
        pass
    
class PacketParser:
    """
    A class to handle raw packet parsing.
    """
    def __init__(self):
        self.packet_parsers = {}
        self.__setup_parsers()

    def __setup_parsers(self):
        self.packet_parsers[HON_SC_INITIAL_STATUS] = self.parse_initial_status
        self.packet_parsers[HON_SC_PING] = self.parse_ping
        self.packet_parsers[HON_SC_TOTAL_ONLINE] = self.parse_total_online
        self.packet_parsers[HON_SC_WHISPER] = self.parse_whisper
    
    def parse_id(self, packet):
        """ 
        Returns the packet's ID.
        The ID is an unsigned short, or a 2 byte integer, which is located at bytes 3 and 4 
        within the packet.
        """
        return struct.unpack('H', packet[2:4])[0]

    def parse_data(self, packet_id, packet):
        """
        Pushes the packet through to a matching registered packet parser, which extracts any useful data 
        into a dict of kwargs which can then be handed to any matching registered event handler.

        TODO: Set up a method of handling oversized packets, this needs to compared the packet size
              given in the first 2 bytes with the amount of data received on the socket, if the sizes do not
              match then subtract the amount received from the total expected size and tell the socket to recv
              that new amount. This all needs to be done before passing the packet to the packet parser.
        """
        # TODO: Move to being a 'socket event' of 'receive'.
        #if 'packet_received' in handler.events:
            #handler.events['packet_received'](packet_id=packet_id, packet=packet)
        
        """ Passes the packet to a packet parser so it can be parsed for data. The returned data
            is then passed to each event handler that requests it as a list of named keywords which
            are taken as arguments.
        """
        if packet_id in self.packet_parsers:
            parser = self.packet_parsers[packet_id]
            data = parser(packet)
            return data
        else:
            # Unknown packet, raise a debug message somehow.
            raise HoNCoreError(12) # Unknown packet received.
    
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

    def parse_ping(self, socket):
        """ Replies to a ping request (0x2A00) with a pong response (0x2A01) """
        return {}

    def parse_total_online(self, packet):
        """ Gets the number of players online """
        count = struct.unpack('I', packet[4:8])[0]
        return {'players_online' : count}

    def parse_whisper(self, packet):
        """ A normal whisper from anyone """
        print "Parsing whisper"
        c = Struct("packet", ULInt16("size"), ULInt16("packetid"), CString("name"), CString("message"))
        r = c.parse(packet)
        return {"name" : r.name, "message" : r.message }

class Event:
    """
    Event objects represent network level events which can have functions connected to them, which
    are then triggered when the event occurs.

    A standard set of events are initialised by the library which should cover nearly everything.
    The core client will store a list of the standard events in client.events.

    The front end client should then connect these events to functions by calling the connect 
    method on the specific event object. e.g.

    self.events.login.connect(self.on_login_event)

    The functions are stored in a list called handlers, each function is ran when the event is triggered.

    On the networking side, the events are triggered after the packet data has been parsed and constructed into useful data.
    The process would be as follows:
    
        packet = sock.recv(512)
        id = parse_id(packet)
        useful_data = raw_parse(id, packet)
        event.trigger(useful_data)

    """
    def __init__(self, name, packet_id):
        self.name = name            # An english, human name for the event. Maybe it can be used for a lookup later. Not sure of a use for it right now.
        self.packet_id = packet_id  # A packet identifier, either a constant or a hex value of a packet. i.e HON_SC_TOTAL_ONLINE or 0x68.
        self.handlers = []          # List of connected handlers.
    
    def __repr__(self):
        return "<%s: %s>" % (self.packet_id, self.name)
    
    def connect(self, function):
        """
        Connects a function to a specific event.
        The event is given as an english name, which corresponds
        to a constant in the packet definition file.
        """
        self.handlers.append(function)

    def disonnect(self, function):
        """
        Hopefully it can be used to remove event handlers from this event
        object so they are no longer triggered. Useful if say, an event only 
        needs to be fired once, for a reminder or such.
        """
        pass
    
    def trigger(self, **data):
        """
        Call each event handler function in the list and pass the keyword argument based data to it.
        """
        for f in self.handlers:
            num_args = f.func_code.co_argcount
            f(**data) if num_args > 0 else f()


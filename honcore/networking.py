import struct, time, threading, thread, socket
from exceptions import *
from packetdef import *
from user import id2nick
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
    A threaded listener class. Enables the receiving and parsing
    of packets to be done in the background.
    Receives the packet and in an addition thread parses the packet
    and triggers any event handlers.
    """
    def __init__(self, chat_socket):
        threading.Thread.__init__(self, name='SocketListener')
        self.chat_socket = chat_socket
        self.stopped = False

    def __repr__(self):
        return "<SocketListener on socket %s>" % self.chat_socket.socket

    def run(self):
        while not self.stopped:
            try:
                packet = self.chat_socket.recv(512)
                if not packet:
                    #print "Empty packet received, socket terminated."
                    self.stopped = True
                    break
                #print "Packet 0x%x on socket %s" % (struct.unpack('H', packet[2:4])[0], self.chat_socket.socket)
                threading.Thread(target=self.chat_socket.parse_packet, name='PacketParser', args=(packet,)).start()
                #self.chat_socket.parse_packet(packet)
            except socket.timeout, e:
                #print "Socket.timeout: %s" % e
                continue
            except socket.error, e:
                #print "Socket.error: %s" % e
                break

class ChatSocket:
    """
    Represents the socket connected to the chat server.
    This object will be created once with the client, and only one will 
    be maintained, however the socket and listener will be re-created for
    each connection used. GC should pick up the old and unused ones.

    The ChatSocket holds two state flags.
        `connected` Represents the state of the actual socket.
        `authenticated` Represents the state of the chat server, and if it 
                        is happy to communicate.
    Both states are used to consider if the connection is available.
    """
    def __init__(self, client_events):
        self.socket = None
        self.connected = False
        self.authenticated = False
        self.listener = None
        self.packet_parser = PacketParser()
        self.events = client_events

        # Transparently connect the ping event to the pong sender.
        self.events[HON_SC_PING].connect(self.send_pong)

        # Some internal handling of the authentication process is also needed
        self.events[HON_SC_AUTH_ACCEPTED].connect(self.on_auth_accepted)

    @property
    def is_authenticated(self):
        """ 
        The ChatSocket becomes authenticated with the Chat Server once
        the `auth_accepted` packet has been received. The ChatSocket will
        then be authenticated until the connection is lost.
        """
        return self.authenticated

    @property
    def is_connected(self): 
        """
        Upon forgetting to connect the ping handler, it is possible to
        see the effects of a ping timeout. This means the socket can be terminated
        early by the server, but at this time it will just leave the program
        hanging. This is_connected method needs to be expanded to check for ping
        timeouts possibly, or simply if the socket is still connected or the 
        socket listener is still running.

        28.10.11 -- There seems to be a bug with HoN's chat server. 
        When two clients wish to connect to the chat server with the same
        credentials, one will get the connection, while the other will enter
        a strange loop of "Connecting.... Disconnected.." 
        The same can be seen using the S2 client and my own clients.
        The behaviour I remember and would expect is that, since each client's reconnect
        cycle is staggered by 30 seconds, the connection would ping-poing between the two
        clients every 30 seconds. Each client would hold the connection for 30 seconds.
        """
        # The socket has been broken early.
        if self.listener.stopped is True and self.connected is True:
            self.connected = False
            self.authenticated = False
        return self.connected

    def connect(self, address, port):
        """
        Creates a connection to the chat server and starts listening for packets.
        At the moment it is VITAL that the authentication is sent within a second or two
        of connecting to the socket, otherwise it will simply hang up.
        But this is done anyway, in the client's connect event.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #self.socket.bind(("", 0))
            self.socket.connect((address, port))
        except socket.timeout:
            raise HoNCoreError(11)
        except socket.error, e:
            if e.errno == 110:
                raise HoNCoreError(11) # Socket timed out
            raise HoNCoreError(10) # Socket error
        
        # The socket is now actually connected.
        self.connected = True

        # Set up a listener as the socket can send data now.
        self.listener = SocketListener(self)
        self.listener.start()

    def disconnect(self):
        """
        Disconnecting should not fail, it's a pretty forced procedure.
        Set the internal state of the socket to be disabled, and set
        authenticated to False.
        Clear the socket object and listener so they can be dereferenced.
        """

        self.connected = False
        self.authenticated = False

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error, e:
            raise HoNCoreError(10) # Socket Error
        finally:
            self.socket = None

        self.listener.stopped = True
        self.listener.join()
        self.listener = None
    
    def send(self, data):
        """ 
        Wrapper send method. 
        TODO: Capture failed sends.
        TODO: Possibly check for the authentication first, and authenticate if required.
        """
        #print "Sending on socket %s from thread %s" % (self.socket, threading.currentThread().getName())
        try:
            self.socket.send(data)
        except socket.error, e:
            #print "Socket error %s while sending." % e
            raise
        return True
    
    def recv(self, buf_size):
        """
        Wrapper recv method.
        TODO: Capture failed recvs
        """
        try:
            data = self.socket.recv(buf_size)
            return data
        except socket.error:
            raise
        except socket.timeout:
            raise

    def parse_packet(self, packet):
        """ Core function to tie together all of the packet parsing. """
        packet_id = self.packet_parser.parse_id(packet)
            
        try:
            packet_data = self.packet_parser.parse_data(packet_id, packet)
        except HoNCoreError, e:
            if e.code == 12: # Unknown packet received.    
                return False

        if packet_data is None:
            return
        
        if packet_id in self.events:
            event = self.events[packet_id]
            event.trigger(**packet_data)

    def on_auth_accepted(self, *p):
        """ Set the authenticated state to True"""
        self.authenticated = True

    def send_pong(self):
        self.send(struct.pack('H', HON_CS_PONG))
    
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
            self.send(packet)
        except socket.error, e:
            if e.errno == 32:
                raise ChatServerError(206)

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
        self.__packet_parsers = {}
        self.__setup_parsers()

    def __setup_parsers(self):
        """ Add every known packet parser to the list of availble parsers. """
        self.__add_parser(HON_SC_AUTH_ACCEPTED, self.parse_auth_accepted)
        self.__add_parser(HON_SC_PING, self.parse_ping)
        self.__add_parser(HON_SC_CHANNEL_MSG, self.parse_channel_message)
        self.__add_parser(HON_SC_CHANGED_CHANNEL, self.parse_changed_channel)
        self.__add_parser(HON_SC_JOINED_CHANNEL, self.parse_joined_channel)
        self.__add_parser(HON_SC_LEFT_CHANNEL, self.parse_left_channel)
        self.__add_parser(HON_SC_WHISPER, self.parse_whisper)
        self.__add_parser(HON_SC_WHISPER_FAILED, self.parse_whisper_failed)
        self.__add_parser(HON_SC_INITIAL_STATUS, self.parse_initial_status)
        self.__add_parser(HON_SC_UPDATE_STATUS, self.parse_update_status)
        self.__add_parser(HON_SC_CLAN_MESSAGE, self.parse_clan_message)
        self.__add_parser(HON_SC_LOOKING_FOR_CLAN, self.parse_looking_for_clan)
        self.__add_parser(HON_SC_PM, self.parse_private_message)
        self.__add_parser(HON_SC_PM_FAILED, self.parse_private_message_failed)
        self.__add_parser(HON_SC_WHISPER_BUDDIES, self.parse_whisper_buddies)
        self.__add_parser(HON_SC_MAX_CHANNELS, self.parse_max_channels)
        self.__add_parser(HON_SC_USER_INFO_NO_EXIST, self.parse_user_info_no_exist)
        self.__add_parser(HON_SC_USER_INFO_OFFLINE, self.parse_user_info_offline)
        self.__add_parser(HON_SC_USER_INFO_ONLINE, self.parse_user_info_online)
        self.__add_parser(HON_SC_USER_INFO_IN_GAME, self.parse_user_info_ingame)
        self.__add_parser(HON_SC_CHANNEL_UPDATE, self.parse_channel_update)
        self.__add_parser(HON_SC_CHANNEL_UPDATE_TOPIC, self.parse_channel_update_topic)
        self.__add_parser(HON_SC_CHANNEL_KICK, self.parse_channel_kick)
        self.__add_parser(HON_SC_CHANNEL_BAN, self.parse_channel_ban)
        self.__add_parser(HON_SC_CHANNEL_UNBAN, self.parse_channel_unban)
        self.__add_parser(HON_SC_CHANNEL_BANNED, self.parse_channel_banned)
        self.__add_parser(HON_SC_CHANNEL_SILENCED, self.parse_channel_silenced)
        self.__add_parser(HON_SC_CHANNEL_SILENCE_LIFTED, self.parse_channel_silence_lifted)
        self.__add_parser(HON_SC_CHANNEL_SILENCE_PLACED, self.parse_channel_silence_placed)
        self.__add_parser(HON_SC_MESSAGE_ALL, self.parse_message_all)
        self.__add_parser(HON_SC_CHANNEL_PROMOTE, self.parse_channel_promote)
        self.__add_parser(HON_SC_CHANNEL_DEMOTE, self.parse_channel_demote)
        self.__add_parser(HON_SC_CHANNEL_AUTH_ENABLE, self.parse_channel_auth_enable)
        self.__add_parser(HON_SC_CHANNEL_AUTH_DISABLE, self.parse_channel_auth_disable)
        self.__add_parser(HON_SC_CHANNEL_AUTH_ADD, self.parse_channel_auth_add)
        self.__add_parser(HON_SC_CHANNEL_AUTH_DELETE, self.parse_channel_auth_delete)
        self.__add_parser(HON_SC_CHANNEL_AUTH_LIST, self.parse_channel_auth_list)
        self.__add_parser(HON_SC_CHANNEL_PASSWORD_CHANGED, self.parse_channel_password_changed)
        self.__add_parser(HON_SC_CHANNEL_AUTH_ADD_FAIL, self.parse_channel_auth_add_fail)
        self.__add_parser(HON_SC_CHANNEL_AUTH_DEL_FAIL, self.parse_channel_auth_del_fail)
        self.__add_parser(HON_SC_JOIN_CHANNEL_PASSWORD, self.parse_join_channel_password)
        self.__add_parser(HON_SC_CHANNEL_EMOTE, self.parse_channel_emote)
        self.__add_parser(HON_SC_TOTAL_ONLINE, self.parse_total_online)
        self.__add_parser(HON_SC_REQUEST_NOTIFICATION, self.parse_request_notification)
        self.__add_parser(HON_SC_NOTIFICATION, self.parse_notification)
    
    def __add_parser(self, packet_id, function):
        """ 
        Registers a parser function for the specified packet. 
        Ensures that only one parser exists for each packet.
        """
        if packet_id in self.__packet_parsers:
            return False
        self.__packet_parsers[packet_id] = function

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
        if packet_id in self.__packet_parsers:
            parser = self.__packet_parsers[packet_id]
            data = parser(packet)
            return data
        else:
            # Unknown packet, raise a debug message somehow.
            raise HoNCoreError(12) # Unknown packet received.
    
    def parse_auth_accepted(self, packet):
        """ The initial response from the chat server to verify that the authentication was accepted. """
        return {}

    def parse_ping(self, packet):
        """ Pings sent every minute. Respond with pong. """
        return {}

    def parse_channel_message(self, packet):
        pass
    
    def parse_changed_channel(self, packet):
        pass

    def parse_joined_channel(self, packet):
        pass

    def parse_left_channel(self, packet):
        pass

    def parse_whisper(self, packet):
        """ 
        A normal whisper from anyone.
        Returns two variables.
            `player`    The name of the player who sent the whisper.
            `message`   The full message sent in the whisper
        """
        c = Struct("packet", ULInt16("size"), ULInt16("packetid"), CString("name"), CString("message"))
        r = c.parse(packet)
        return {"player" : r.name, "message" : r.message }

    def parse_whisper_failed(self, packet):
        pass

    def parse_initial_status(self, packet):
        """ 
        The initial status packet contains information for all available buddy and clan members, 
        as well as some server statuses and matchmaking settings.
        """
        contact_count = int(struct.unpack_from('I', packet[4:8])[0]) # Tuples?
        contact_data = packet[8:]
        if contact_count > 0:
            i = 1
            #print("Parsing data for %i contacts." % contact_count)
            while i <= int(contact_count):
                status = int(struct.unpack_from('B', contact_data[4])[0])
                nick = ""
                gamename = ""
                flag = ""
                if status == HON_STATUS_INLOBBY or status == HON_STATUS_INGAME:
                    c = Struct("buddy", ULInt32("buddyid"), Byte("status"), Byte("flag"), CString("server"), CString("gamename"))
                    r = c.parse(contact_data)
                    nick = id2nick(r.buddyid)
                    flag = str(r.flag)
                    contact_data = contact_data[6 + (len(r.server)+1+len(r.gamename)+1):]
                    gamename = r.gamename
                else:
                    c = Struct("buddy", ULInt32("buddyid"), Byte("status"), Byte("flag"))
                    r = c.parse(contact_data[:6])
                    nick = id2nick(r.buddyid)
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

    def parse_update_status(self, packet):
        pass

    def parse_clan_message(self, packet):
        pass

    def parse_looking_for_clan(self, packet):
        pass

    def parse_private_message(self, packet):
        """ 
        A private message from anyone.
        Returns two variables.
            `player`    The name of the player who sent the whisper.
            `message`   The full message sent in the whisper
        """
        c = Struct("packet", ULInt16("size"), ULInt16("packetid"), CString("name"), CString("message"))
        r = c.parse(packet)
        return {"player" : r.name, "message" : r.message }

    def parse_private_message_failed(self, packet):
        pass

    def parse_whisper_buddies(self, packet):
        pass

    def parse_max_channels(self, packet):
        pass

    def parse_user_info_no_exist(self, packet):
        pass

    def parse_user_info_offline(self, packet):
        pass

    def parse_user_info_online(self, packet):
        pass

    def parse_user_info_ingame(self, packet):
        pass

    def parse_channel_update(self, packet):
        pass

    def parse_channel_update_topic(self, packet):
        pass

    def parse_channel_kick(self, packet):
        pass

    def parse_channel_ban(self, packet):
        pass

    def parse_channel_unban(self, packet):
        pass

    def parse_channel_banned(self, packet):
        pass

    def parse_channel_silenced(self, packet):
        pass

    def parse_channel_silence_lifted(self, packet):
        pass

    def parse_channel_silence_placed(self, packet):
        pass

    def parse_message_all(self, packet):
        pass

    def parse_channel_promote(self, packet):
        pass

    def parse_channel_demote(self, packet):
        pass

    def parse_channel_auth_enable(self, packet):
        pass

    def parse_channel_auth_disable(self, packet):
        pass

    def parse_channel_auth_add(self, packet):
        pass

    def parse_channel_auth_delete(self, packet):
        pass

    def parse_channel_auth_list(self, packet):
        pass

    def parse_channel_password_changed(self, packet):
        pass

    def parse_channel_auth_add_fail(self, packet):
        pass

    def parse_channel_auth_del_fail(self, packet):
        pass

    def parse_join_channel_password(self, packet):
        pass

    def parse_channel_emote(self, packet):
        pass
    
    def parse_total_online(self, packet):
        """ Gets the number of players online """
        count = struct.unpack('I', packet[4:8])[0]
        return {'players_online' : count}
    
    def parse_request_notification(self, packet):
        pass

    def parse_notification(self, packet):
        pass


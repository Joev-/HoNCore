""" 
HoNCore. Python library providing connectivity and functionality
with HoN's chat server.

Copyright (c) 2011 Joseph Vaughan.

This file is part of HoNCore.

HoNCore is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

HoNCore is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with HoNCore.  If not, see <http://www.gnu.org/licenses/>.
"""

import struct, time, threading, thread, socket
from exceptions import *
from constants import *
from common import User
from lib.construct import *


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
        self.events[HON_SC_PING].connect(self.send_pong, priority=1)

        # Some internal handling of the authentication process is also needed
        self.events[HON_SC_AUTH_ACCEPTED].connect(self.on_auth_accepted, priority=1)

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
        
        # Trigger a general event on all packets. Passes the raw packet.
        try:
            self.events[HON_SC_PACKET_RECV].trigger(**{'packet_id': packet_id, 'packet': packet})
        except KeyError:
            pass
        
        # Trim the length and packet id from the packet
        packet = packet[4:]
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
    
    def send_whisper(self, player, message):
        """
        Sends the message to the player in the form of a whisper.
        Takes 2 parameters.
            `player`    A string containing the player's name.
            `message`   A string containing the message.
        Packet ID is 0x08 or HON_CS_WHISPER.
        """

        c = Struct("whisper",
           ULInt16("id"),
           String("player", len(player)+1, encoding="utf8", padchar="\x00"),
           String("message", len(message)+1, encoding="utf8", padchar="\x00")
        )
        packet = c.build(Container(id=HON_CS_WHISPER, player=unicode(player), message=unicode(message)))
        self.send(packet)

    def send_auth_info(self, account_id, cookie, ip, auth_hash, protocol, invis):
        """ 
        Sends the chat server authentication request.
        Takes 6 parameters.
            `account_id`    An integer containing the player's account ID.
            `cookie`        A 33 character string containing a cookie.
            `ip`            A string containing the player's IP address.
            `auth`          A string containing an authentication hash.
            `protocol`      An integer containing the protocol version to be used.
            `invis`         A boolean value, determening if invisible mode is used.
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

    def send_private_message(self, player, message):
        """
        Sends the message to the player in the form of a private message.
        Packet ID: 0x1C
        """
        c = Struct("private_message",
               ULInt16("id"),
               String("player", len(player)+1, encoding="utf8", padchar="\x00"),
               String("message", len(message)+1, encoding="utf8", padchar="\x00")
            )
        packet = c.build(Container(id=HON_CS_PM, player=unicode(player), message=unicode(message)))
        self.send(packet)


    def send_join_channel(self, channel):
        """
        Sends a request to join the channel.
        """
        c = Struct("join_channel",
                ULInt16("id"),
                String("channel", len(channel)+1, encoding="utf8", padchar="\x00")
            )
        packet = c.build(Container(id=HON_CS_JOIN_CHANNEL, channel=unicode(channel)))
        self.send(packet)

    def send_whisper_buddies(self):
        pass

    def send_leave_channel(self, channel):
        """
        Leaves the channel `channel`.
        Packet ID: 0x22 or HON_CS_LEAVE_CHANNEL
        """
        c = Struct("leave_channel",
               ULInt16("id"),
               String("channel", len(channel)+1, encoding="utf8", padchar="\x00")
            )
        packet = c.build(Container(id=HON_CS_LEAVE_CHANNEL, channel=unicode(channel)))
        self.send(packet)

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

    def send_join_channel_password(self, channel, password):
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
        self.__add_parser(HON_SC_JOINED_CHANNEL, self.parse_joined_channel)
        self.__add_parser(HON_SC_ENTERED_CHANNEL, self.parse_entered_channel)
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
        
        """ Passes the packet to a packet parser so it can be parsed for data. The returned data
            is then passed to each event handler that requests it as a list of named keywords which
            are taken as arguments.
        """
        if packet_id in self.__packet_parsers:
            parser = self.__packet_parsers[packet_id]
            data = parser(packet)
            return data
        else:
            raise HoNCoreError(12) # Unknown packet received.
    
    def parse_auth_accepted(self, packet):
        """ The initial response from the chat server to verify that the authentication was accepted. """
        return {}

    def parse_ping(self, packet):
        """ Pings sent every minute. Respond with pong. """
        return {}

    def parse_channel_message(self, packet):
        """
        Triggered when a message is sent to a channel that the user
        is currently in.
        Returns the following:
            `account_id`    The ID of player account who sent the message.
            `channel_id`    The ID of the channel message was sent to.
            `message`       The message sent.
        """
        c = Struct('channel_message',
                   ULInt32('account_id'),
                   ULInt32('channel_id'),
                   CString('message')
                  )
        r = c.parse(packet)
        return {
            'account_id': r.account_id,
            'channel_id': r.channel_id,
            'message'   : r.message
        }
    
    def parse_joined_channel(self, packet):
        """
        Triggered when `the user` joins a channel.
        Returns the following:
            `channel`       Name of the channel joined.
            `channel_id`    The ID of the channel joined.
            `topic`         The topic set for the channel.
            `operators`     A list of operators in the channel and the data regarding them.
            `users`         A list of users in the channel and data regarding them.
        """
        c = Struct('changed_channel', 
                CString('channel_name'), 
                ULInt32('channel_id'), 
                ULInt8('unknown'), 
                CString('channel_topic'), 
                ULInt32('op_count'),
                MetaRepeater(lambda ctx: ctx['op_count'],
                    Struct('op_users',
                        ULInt32('op_aid'),
                        Byte('op_type')
                    )
                ),
                ULInt32('user_count'),
                MetaRepeater(lambda ctx: ctx['user_count'],
                    Struct('users',
                        CString('nickname'),
                        ULInt32('id'),
                        Byte('status'),
                        Byte('flags'),
                        CString('chat_icon'),
                        CString('nick_colour'),
                        CString('account_icon')
                    )
                )
            )
        r = c.parse(packet)
         
        return {
            'channel': r.channel_name,
            'channel_id': r.channel_id,
            'topic': r.channel_topic,
            'operators': [op for op in r.op_users],
            'users': [User(u.id, u.nickname, u.status, u.flags, u.chat_icon,
                           u.nick_colour, u.account_icon) for u in r.users],
        }

    def parse_entered_channel(self, packet):
        """
        When another user joins a channel.
        Returns the following:
            `channel_id`    The ID of the channel that the user joined.
            `user`          A `User` object containing the user that joined.
        """
        c = Struct('entered_channel',
                CString('u_nickname'),
                ULInt32('u_id'),
                ULInt32('channel_id'),
                Byte('u_status'),
                Byte('u_flags'),
                CString('u_chat_icon'),
                CString('u_nick_colour'),
                CString('u_account_icon')
            )
        r = c.parse(packet)
        u = User(r.id, r.u_nickname, r.u_status, r.u_flags, r.u_chat_icon,
                      r.u_nick_colour, r.u_account_icon)
        return {'channel_id': r.channel_id, 'user': u}

    def parse_left_channel(self, packet):
        pass

    def parse_whisper(self, packet):
        """ 
        A normal whisper from anyone.
        Returns two variables.
            `player`    The name of the player who sent the whisper.
            `message`   The full message sent in the whisper
        """
        c = Struct("packet", CString("name"), CString("message"))
        r = c.parse(packet)
        return {"player" : r.name, "message" : r.message }

    def parse_whisper_failed(self, packet):
        pass

    def parse_initial_status(self, packet):
        """ 
        The initial status packet contains information for all available buddy and clan members, 
        as well as some server statuses and matchmaking settings.
        """
        #c = Struct('initial_status',
                #ULInt32('user_count'),
                #MetaRepeater(lambda ctx: ctx['user_count'],
                    #Struct('users',
                        #ULInt32('id'),
                        #Byte('status'),
                        #Byte('flags'),
                        #If(lambda ctx: ctx['status'] == HON_STATUS_INGAME or ctx['status'] == 5,
                           #CString('server'),
                           #CString('game_name')
                        #)
                    #)
                #),
                


        return {}

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
        c = Struct("packet", String("name"), CString("message"))
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
        c = Struct("players_online",
               ULInt32('count'),
               CString('regions')
            )
        r = c.parse(packet)
        return {'count': r.count, 'region_data': r.regions} 
    
    def parse_request_notification(self, packet):
        pass

    def parse_notification(self, packet):
        pass


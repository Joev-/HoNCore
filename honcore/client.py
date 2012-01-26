"""
HoNCore. Python library providing connectivity and functionality
with HoN's chat server.
"""

import sys, struct, socket, time
import deserialise, common
from requester import Requester
from networking import ChatSocket
from constants import *
from exceptions import *

__all__ = ['HoNClient']

_config_defaults = {
    "chatport" : 11031, 
    "protocol" : 21, 
    "invis" : False,
}

class HoNClient(object):    
    def __init__(self):
        self.config = _config_defaults
        self.__events = {}
        self.__create_events()
        self.__setup_events()
        self.__chat_socket = ChatSocket(self.__events)
        self.__listener = None
        self.__requester = Requester()
        self.account = None
        self.__channels = {}
        self.__users = {}

    def __create_events(self):
        """ Create each event that can be triggered by the client.
            As more packets are reverse engineered they should be added here so that 
            the client can handle them.
        """
        self.__events[HON_SC_AUTH_ACCEPTED] = Event("Auth Accepted", HON_SC_AUTH_ACCEPTED)
        self.__events[HON_SC_PING] = Event("Ping", HON_SC_PING)
        self.__events[HON_SC_CHANNEL_MSG] = Event("Channel Message", HON_SC_CHANNEL_MSG)
        self.__events[HON_SC_JOINED_CHANNEL] = Event("Join Channel", HON_SC_JOINED_CHANNEL)
        self.__events[HON_SC_ENTERED_CHANNEL] = Event("Entered Channel", HON_SC_ENTERED_CHANNEL)
        self.__events[HON_SC_LEFT_CHANNEL] = Event("Left Channel", HON_SC_LEFT_CHANNEL)
        self.__events[HON_SC_WHISPER] = Event("Whisper", HON_SC_WHISPER)
        self.__events[HON_SC_PM] = Event("Private Message", HON_SC_PM)
        self.__events[HON_SC_MESSAGE_ALL] = Event("Server Message", HON_SC_MESSAGE_ALL)
        self.__events[HON_SC_TOTAL_ONLINE] = Event("Total Online", HON_SC_TOTAL_ONLINE)
        self.__events[HON_SC_PACKET_RECV] = Event("Packet Received", HON_SC_PACKET_RECV)

    def __setup_events(self):
        """ Transparent handling of some data is needed so that the client
            can track things such as users and channels.
        """
        self.connect_event(HON_SC_JOINED_CHANNEL, self.__on_joined_channel, priority=1)
        self.connect_event(HON_SC_ENTERED_CHANNEL, self.__on_entered_channel, priority=1)

    def __on_initial_statuses(self, users):
        """ Sets the status and flags for each user. """
        for account_id in users:
            if account_id in self.__users:
                user = self.__users[account_id]
                user.status = users[account_id]['status']
                user.flags = users[account_id]['flags']
    
    def __on_joined_channel(self, channel, channel_id, topic, operators, users):
        """ Channel names, channel ids, user nicks and user account ids need to be
            contained in a hash table/dict so they can be looked up later when needed.
        """
        self.__channels[channel_id] = channel
        for user in users:
            if user.account_id not in self.__users:
                self.__users[user.account_id] = user

    def __on_entered_channel(self, channel_id, user):
        """ Transparently add the id and nick of the user who entered the channel to
            the users dictionary.
        """
        if user.account_id not in self.__users:
            self.__users[user.account_id] = user

    def _configure(self, *args, **kwargs):
        """ Set up some configuration for the client and the requester. 
            The requester configuration is not really needed, but just incase
            it does change in the future.
        """
        config_map = {
            "chatport" : self.config,
            "protocol" : self.config,
            "invis" : self.config,
            "masterserver" : self.__requester.config,
            "basicserver" : self.__requester.config,
            "honver" : self.__requester.config
        }
        
        for kwarg in kwargs:
            if kwarg in config_map:
                config_map[kwarg][kwarg] = kwargs[kwarg]

    """ Master server related functions. """
    def _login(self, username, password):
        """ HTTP login request to the master server.
            Catches the following:
                * Failed to get login data after 3 attempts.
                * Could not connect to the masterserver.
                * Could not obtain login data
                * Incorrect username/password
        """
        attempts = 1
        while True:
            try:
                response = self.__requester.login(username, password)
                break
            except MasterServerError:
                if attempts == 3:
                    raise   # Re-raise the last exception given
                timeout = pow(2, attempts)
                time.sleep(timeout)
                attempts += 1

        if response == None:
            raise MasterServerError(100)
        elif response == "":
            raise MasterServerError(101)

        # Pass the data to the deserialiser
        try:
            self.account, new_users = deserialise.parse(response)
            self.account.logged_in = True
        except MasterServerError:
            raise MasterServerError(101)

        for user in new_users:
            self.__users[user.account_id] = user

        return True

    def _logout(self):
        """ Send a logout request to the masterserver and log out the account.
            Is forcing the logout okay? Breaking the connection to the chat server technically 
            logs the user out... What is the effect of sending the logout request to the masterserver?
            TODO: Fail cases, handle them!
                * Connection timed out
                * Connection refused.
        """
        if self.account == None:
            return
        
        if not self.account.cookie:
            self.account.logged_in = False
        else:
            attempts = 0
            while True:
                try:
                    self.__requester.logout(self.account.cookie)
                    self.account.logged_in = False
                    break
                except MasterServerError, e:
                    if attempts == 3:
                        # Force the logout and raise the error
                        self.account.logged_in = False
                        raise   # Re-raise the last exception given
                        break
                    timeout = pow(2, attempts)
                    time.sleep(timeout)
                    attempts += 1

    """ Chatserver related functions"""
    def _chat_connect(self):
        """ Sends the initial authentication request to the chatserver via the chat socket object.

            Ensures the user information required for authentication is available, otherwise raises
            a ChatServerError #205 (No cookie/auth hash provided)

            If for some reason a ChatSocket does not exist then one is created.
            Connects that chat socket to the correct address and port. Any exceptions are raised to the top method.
            Finally sends a valid authentication packet. Any exceptions are raised to the top method.
        """
        if self.account == None or self.account.cookie == None or self.account.auth_hash == None:
            raise ChatServerError(205)
       
        if self.__chat_socket is None:
            self.__chat_socket = ChatSocket(self.events)
        try:
            self.__chat_socket.connect(self.account.chat_url, self.config['chatport']) # Basic connection to the socket
        except HoNCoreError as e:
            if e.code == 10: # Socket error.
                raise ChatServerError(208) # Could not connect to the chat server.
            elif e.code == 11: # Socket timed out.
                raise ChatServerError(201)
            
        # Send initial authentication request to the chat server.
        # TODO: If the chat server did not respond to the auth request after a set number of attempts then increment the chat protocol version.
        try:
            self.__chat_socket.send_auth_info(self.account.account_id, self.account.cookie, self.account.ip, self.account.auth_hash,  self.config['protocol'], self.config['invis'])
        except ChatServerError:
            raise # Re-raise the exception.
        
        # The idea is to give 10 seconds for the chat server to respond to the authentication request.
        # If it is accepted, then the `is_authenticated` flag will be set to true.
        # NOTE: Lag will make this sort of iffy....
        attempts = 1
        while attempts is not 10:
            if self.__chat_socket.is_authenticated:
                return True
            else:
                time.sleep(1)
                attempts += 1
        raise ChatServerError(200) # Server did not respond to the authentication request 
        
    def _chat_disconnect(self):
        """ Disconnect gracefully from the chat server and close & remove the socket."""
        if self.__chat_socket is not None:
            self.__chat_socket.connected = False # Safer to stop the thread with this first.
            try:
                self.__chat_socket.socket.shutdown(socket.SHUT_RDWR)
                self.__chat_socket.socket.close()
            except socket.error:
                raise ChatServerError(209)

    @property
    def is_logged_in(self):
        """
        Override this and provide a way to handle being logged in.
        """
        pass

    @property
    def is_connected(self):
        """ Test for chat server connection. 

            The line of thought here is, the client can not be connected to the chat server
            until it is authenticated, the chat socket can be connected as long as the server
            doesn't deny or drop the connection.

            Once a user is logged in to a HoN client, they can be logged in but not connected.

            This would happen if a chat server connection is dropped unexpectedly or is never initialised.
            The main program would use this to check for that and then handle it itself.
        """
        # Check the socket exists.
        if self.__chat_socket is None:
            return False
        # Ensure the user is authenticated against the chat server
        if self.__chat_socket.is_authenticated is False:
            return False
        # Check the status of the chat socket object.
        if self.__chat_socket.is_connected is False:
            return False
        # Any other checks to be done..? 
        return True

    """ Message of the day related functions"""
    def motd_get(self):
        """ Requests the message of the day entries from the server and then pushes them through motd_parse.
            Returns a dict of motd entries.
        """
        raw = self.__requester.motd()
        try:
            raw = deserialise.parse_raw(raw)
        except ValueError:
            raise MasterServerError(108)
        return self.__motd_parse(raw)

    def __motd_parse(self, raw):
        """ Parses the message of the day entries into a dictionary of the format:
            motd = {
                motd_list = [
                    {
                        ["title"] = "Item 1 title",
                        ["author"] = "MsPudding",
                        ["date"] = "6/30/2011"
                        ["body"] = "This is the body of the message including line feeds"
                    },
                    {
                        ["title"] = "Item 2 title", 
                        ["author"] = "Konrar",
                        ["date"] = "6/29/2011",
                        ["body"] = "This is the body text Sometimes there are ^rColours^*"
                    }
                ],
                image = "http://icb.s2games.com/motd/4e67cffcc959e.jpg",
                server_data = "We are aware of the server issues....",
                honcast = 0
            }
            The first index will always be the newest....... Right?
        """
        motd = {'motd_list': [], 'image': '', 'server_data': '', 'honcast': 0}
        # Split the full string into a list of entries.
        for entry in raw['motddata'].split("|"):
            #try:
            title, body, author, date = entry.split("`")
            motd['motd_list'].append({"title" : title, "author" : author, "date" : date, "body" : body})
            #except ValueError:
                #raise MasterServerError(113) # Motd data error
        motd['image'] = raw['motdimg']
        motd['server_data'] = raw['serverdata']
        motd['honcast'] = raw['honcast']
        return motd

    """ The core client functions."""
    def send_channel_message(self, message, channel_id):
        """ Sends a message to a specified channel.
            Takes 2 parameters.
                `message`   The message to be send.
                `channel_id`   The id of the channel to send it to.
        """
        # TODO: Implement throttling for messages.
        self.__chat_socket.send_channel_message(message, channel_id)

    def join_channel(self, channel, password=None):
        """ Sends a request to join a channel.
            
            Takes 2 paramters.
                `channel`   A string containing the channel name.
                `password`  The optional password required to join the channel.
        """
        if password:
            self.__chat_socket.send_join_channel_password(channel, password)
        elif not password:
            self.__chat_socket.send_join_channel(channel)

    def send_whisper(self, player, message):
        """ Sends the message to the player.
            Takes 2 parameters.
                `player`    A string containing the player's name.
                `message`   A string containing the message.
        """
        self.__chat_socket.send_whisper(player, message)

    def send_private_message(self, player, message):
        """ Sends the message to the player.
            Takes 2 parameters.
                `player`    A string containing the player's name.
                `message`   A string containing the message.
        """
        self.__chat_socket.send_private_message(player, message)

    """ Utility functions """
    def connect_event(self, event_id, method, priority=5):
        """ Wrapper method for connecting events. """
        try:
            self.__events[event_id].connect(method, priority)
        except KeyError:
            raise HoNCoreError(13) # Unknown event ID 
    
    def disconnect_event(self, event_id, method):
        """ Wrapper method for disconnecting events. """
        try:
            self.__events[event_id].disconnect(method)
        except HoNCoreError, e:
            if e.id == 14: # Method is not connected to this event.
                raise
        except KeyError:
            raise HoNCoreError(13) # Unknown event ID

    def id_to_channel(self, channel_id):
        """ Wrapper function to return the channel name for the given ID.
            If no channel was found then return None
        """
        try:
            return self.__channels[channel_id]
        except KeyError:
            return None

    def id_to_nick(self, account_id):
        """ Wrapper function to return the nickname for the user associated with that account ID.
            If no nickname was found then return None
        """
        try:
            return self.__users[account_id].nickname
        except KeyError:
            return None

    def id_to_user(self, account_id):
        """ Wrapper function to return the user object for the user associated with that account ID.
            If no user was found then return None
        """
        try:
            return self.__users[account_id]
        except KeyError:
            return None

    def get_buddies(self):
        buddies = []
        for buddy_id in self.account.buddy_list:
            buddies.append(self.__users[buddy_id])
        return buddies

    """ Debugging functions """
    def list_users(self):
        for aid in self.__users:
            print self.__users[aid]

class Event:
    """ Event objects represent network level events which can have functions connected to them, which
        are then triggered when the event occurs.

        A standard set of events are initialised by the library which should cover nearly everything.
        The core client will store a list of the standard events in client.__events.

        Events can have functions connected to them using the client.connect_event method. A constant representing the desired
        event is passed, along with an optional priority.

        The functions are stored in a list called handlers, each function is executed in order of priority, from lowest to highest,
        when the event is triggered.
        Imported events would have a priority of 1, as they would be handled first.
        Less important events could have a priority of 5, while normal events hover around 3 or 4.
        
        This is useful as it allows for core/client events to be processed first to ensure that data is available to the client's 
        internal data before it is used elsewhere in the program, such as in the User Interface.

        On the networking side, the events are triggered after the packet data has been parsed and constructed into useful data.
        The process would be as follows:
        
            packet = sock.recv(512)
            id = parse_id(packet)
            useful_data = raw_parse(id, packet)
            event.trigger(useful_data)
    """

    class ConnectedMethod:
        def __init__(self, method, priority):
            self.method = method
            self.priority = priority
        
        def __repr__(self):
            return "[%s %s]" % (self.method, self.priority)

    def __init__(self, name, packet_id):
        self.name = name            # An english, human name for the event. Maybe it can be used for a lookup later. Not sure of a use for it right now.
        self.packet_id = packet_id  # A packet identifier, either a constant or a hex value of a packet. i.e HON_SC_TOTAL_ONLINE or 0x68.
        self.handlers = []          # List of connected methods.
    
    def __repr__(self):
        return "<%s: %s>" % (self.packet_id, self.name)
    
    def connect(self, function, priority=5):
        """ Connects a function to a specific event.
            The event is given as a constant, that is defined the packet definition file.
        """
        self.handlers.append(self.ConnectedMethod(function, priority))

    def disonnect(self, method):
        """ Hopefully it can be used to remove event handlers from this event
            object so they are no longer triggered. Useful if say, an event only 
            needs to be triggered once, for a reminder or such.
        """
        for cm in self.handlers:
            if cm.method == method:
                self.handlers.remove(cm)
            else:
                raise HoNCoreError(14) # Method is not connected to this event_id
        pass
    
    def trigger(self, **data):
        """ Sorts the connected handlers based on their priority and calls each one in turn,
            passing the dictionary of keyword arguments, or alternatively with no arguments.
        """
        for cm in sorted(self.handlers, key=lambda c: c.priority):
            f = cm.method
            num_args = f.func_code.co_argcount
            f(**data) if num_args > 0 else f()


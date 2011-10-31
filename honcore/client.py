import sys, struct, socket, time
import deserialise, user
from requester import Requester
from networking import ChatSocket
from packetdef import *
from exceptions import *

__all__ = ['HoNClient']

_config_defaults = {
    "chatport" : 11031, 
    "protocol" : 19, 
    "invis" : False,
}

class HoNClient(object):    
    def __init__(self):
        self.config = _config_defaults
        self.events = {}
        self.__create_events()
        self.__setup_events()
        self.__chat_socket = ChatSocket(self.events)
        self.__listener = None
        self.__requester = Requester()
        self.account = None
        self.__channels = {}
        self.__users = {}

    def __create_events(self):
        """ Create each event that can be triggered by the client. """
        self.events[HON_SC_AUTH_ACCEPTED] = Event("Auth Accepted", HON_SC_AUTH_ACCEPTED)
        self.events[HON_SC_PING] = Event("Ping", HON_SC_PING)
        self.events[HON_SC_CHANNEL_MSG] = Event("Channel Message", HON_SC_CHANNEL_MSG)
        self.events[HON_SC_JOINED_CHANNEL] = Event("Join Channel", HON_SC_JOINED_CHANNEL)
        self.events[HON_SC_ENTERED_CHANNEL] = Event("Entered Channel", HON_SC_ENTERED_CHANNEL)
        self.events[HON_SC_LEFT_CHANNEL] = Event("Left Channel", HON_SC_LEFT_CHANNEL)
        self.events[HON_SC_WHISPER] = Event("Whisper", HON_SC_WHISPER)
        self.events[HON_SC_PM] = Event("Private Message", HON_SC_PM)

        self.events[HON_SC_MESSAGE_ALL] = Event("Server Message", HON_SC_MESSAGE_ALL)
    
        self.events[HON_SC_TOTAL_ONLINE] = Event("Total Online", HON_SC_TOTAL_ONLINE)

    def __setup_events(self):
        """
        Transparent handling of some data is needed so that the client
        can track things such as users and channels.
        """
        self.events[HON_SC_JOINED_CHANNEL].connect(self.__on_joined_channel, priority=1)
        self.events[HON_SC_ENTERED_CHANNEL].connect(self.__on_entered_channel, priority=1)
    
    def __on_joined_channel(self, channel, channel_id, topic, operators, users):
        """
        Channel names, channel ids, user nicks and user account ids need to be
        contained in a hash table/dict so they can be looked up later when needed.
        """
        self.__channels[channel_id] = channel

        for user in users:
            self.__users[user.account_id] = user

    def __on_entered_channel(self, channel_id, user):
        """
        Transparently add the id and nick of the user who entered the channel to
        the id2user dictionary.
        """
        self.__users[user.account_id] = user

    def _configure(self, *args, **kwargs):
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
            TODO:   Handle HTTP errors here somewhere.
                    Some can be handled easily with a retry, but if an error shows that the server will never 
                    accept a connection in the near future then it should stop trying to connect.
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
            self.account = deserialise.parse(response)
            self.account.logged_in = True
        except MasterServerError:
            raise MasterServerError(101)

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
        """ 
        Sends the initial authentication request to the chatserver via the chat socket object.
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
        # TODO: If the chat server did not respond to the auth request then increment the chat protocol version.
        # Maybe should be handled by the true client. It would be nice for HoNStatus to be able to see that the protocol was incremented..
        # However maybe it's not so important because I should check it each patch regardless.
        try:
            self.__chat_socket.send_auth_info(self.account.account_id, self.account.cookie, self.account.ip, self.account.auth_hash,  self.config['protocol'], self.config['invis'])
        except ChatServerError:
            raise # Re-raise the exception.
        
        # The idea is to give 5 seconds for the chat server to respond to the authentication request.
        # If it is accepted, then the `is_authenticated` flag will be set to true.
        # NOTE: Lag will make this sort of iffy....
        attempts = 1
        while attempts is not 5:
            if self.__chat_socket.is_authenticated:
                return True
            else:
                time.sleep(1)
                attempts += 1
        raise ChatServerError(200) # Server did not respond to the authentication request 
        
    def _chat_disconnect(self):
        """ Disconnect gracefully from the chat server and close and remove the socket."""
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
        """ 
        Test for chat server connection. 
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
        """ 
        Requests the message of the day entries from the server and then pushes them through motd_parse.
        Returns a dict of motd entries.
        """
        raw = self.__requester.motd()
        try:
            raw = deserialise.parse_raw(raw)
        except ValueError:
            raise MasterServerError(108)
        return self.motd_parse(raw)

    def motd_parse(self, raw):
        """ 
        Parses the message of the day entries into a dictionary of the format:
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
    def join_channel(self, channel, password=None):
        """
        Sends a request to join a channel.
        Takes 2 paramters.
            `channel`   A string containing the channel name.
            `password`  The optional password required to join the channel.
        """
        if password:
            self.__chat_socket.send_join_channel_password(channel, password)
        elif not password:
            self.__chat_socket.send_join_channel(channel)

    def send_whisper(self, player, message):
        """ 
        Sends the message to the player.
        Takes 2 parameters.
            `player`    A string containing the player's name.
            `message`   A string containing the message.
        """
        self.__chat_socket.send_whisper(player, message)

    def send_private_message(self, player, message):
        """
        Sends the message to the player.
        Takes 2 parameters.
            `player`    A string containing the player's name.
            `message`   A string containing the message.
        """
        self.__chat_socket.send_private_message(player, message)

    """ Utility functions """
    def id_to_channel(self, channel_id):
        """
        Wrapper function to return the channel name for the given ID.
        If no channel was found then return None
        """
        try:
            return self.__channels[channel_id]
        except KeyError:
            return None

    def id_to_nick(self, account_id):
        """
        Wrapper function to return the nickname for the user associated
        with that account ID.
        If no nickname was found then return None
        """
        try:
            return self.__users[account_id].nickname
        except KeyError:
            return None

    def id_to_user(self, account_id):
        """
        Wrapper function to return the user object for the user
        associated with that account ID.
        If no user was found then return None
        """
        try:
            return self.__users[account_id]
        except KeyError:
            return None

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

    The functions can be assigned a priority so that they are executed in an order. This is useful for
    ensuring that lower level network/core client related functions are executed first.

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
        """
        Connects a function to a specific event.
        The event is given as an english name, which corresponds
        to a constant in the packet definition file.
        """
        self.handlers.append(self.ConnectedMethod(function, priority))

    def disonnect(self, function):
        """
        Hopefully it can be used to remove event handlers from this event
        object so they are no longer triggered. Useful if say, an event only 
        needs to be fired once, for a reminder or such.
        """
        pass
    
    def trigger(self, **data):
        """
        Sorts the connected handlers based on their priority and calls each one in turn,
        passing the dictionary of keyword arguments, or alternatively with no arguments.
        """
        for f in sorted(self.handlers, key=lambda cm: cm.priority):
            f = f.method
            num_args = f.func_code.co_argcount
            f(**data) if num_args > 0 else f()


import sys, struct, socket, time
import deserialise, user, handler
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
        self.__chat_socket = ChatSocket(self.events)
        self.__listener = None
        self.__requester = Requester()

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
            deserialise.parse(response)
            user.account.logged_in = True
        except MasterServerError:
            raise MasterServerError(101)

    def _logout(self):
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
            attempts = 0
            while True:
                try:
                    self.__requester.logout(user.account.cookie)
                    user.account.logged_in = False
                    break
                except MasterServerError, e:
                    if attempts == 3:
                        # Force the logout and raise the error
                        user.account.logged_in = False
                        raise   # Re-raise the last exception given
                        break
                    timeout = pow(2, attempts)
                    time.sleep(timeout)
                    attempts += 1

    """ Chatserver related functions"""
    def _chat_connect(self):
        """ Sends the initial authentication request to the chatserver via the chat socket object.
            Catches the following:
                * The server responded to the authentication request.
                * The server did not respond to the authentication request.
                * Account data mismatch.
                * Connection to the server timed out.
        """
        if user.account == None or user.account.cookie == None or user.account.auth_hash == None:
            raise ChatServerError(205)
       
        if self.__chat_socket is None:
            self.__chat_socket = ChatSocket(self.events)
        try:
            self.__chat_socket.connect(user.account.chat_url, self.config['chatport']) # Basic connection to the socket
        except HoNCoreError as e:
            if e.code == 10: # Socket error.
                raise ChatServerError(208) # Could not connect to the chat server.
            elif e.code == 11: # Socket timed out.
                raise ChatServerError(201)
            
        # Send initial authentication request to the chat server.
        # TODO: If the chat server did not respond to the auth request then increment the chat protocol version.
        # Maybe should be handled by the true client. It would be nice for HoNStatus to be able to see that the protocol was incremented..
        # However maybe it's not so important because I should check it each patch regardless.
        #attempts = 1
        #while True:
            #try:
                #self.__chat_socket.send_auth_info(user.account.account_id, user.account.cookie, user.account.ip, user.account.auth_hash, self.config['protocol'], self.config['invis'])
                #break
            #except ChatServerError, e:
                #if attempts == 3:
                    #self.__chat_socket.connected = False # Make sure this is set.
                    #if e.code == 206: # Broken Pipe, want to see the message because it's important!
                        #raise
                    #else:
                        #raise ChatServerError(203)
                #timeout = pow(2, attempts)
                #time.sleep(timeout)
                #attempts += 1
        #self.__chat_socket.connected = True
        self.__chat_socket.send_auth_info(user.account.account_id, user.account.cookie, user.account.ip, user.account.auth_hash,  self.config['protocol'], self.config['invis'])

    def _chat_disconnect(self):
        """ Disconnect gracefully from the chat server and close and remove the socket."""
        if self.__chat_socket is not None:
            self.__chat_socket.connected = False # Safer to stop the thread with this first.
            try:
                self.__chat_socket.socket.shutdown(socket.SHUT_RDWR)
                self.__chat_socket.socket.close()
            except socket.error:
                raise ChatServerError(209)
            #finally:
                #self.__chat_socket = None

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
        Once a user is logged in to a HoN client, they can be logged in but not connected.
        This would happen if a chat server connection is dropped unexpectedly or is never initialised.
        The main program would use this to check for that and then handle it itself.
        """
        # Check the socket exists.
        if self.__chat_socket is None:
            return False
        # Check the status of the chat socket object.
        if self.__chat_socket.is_connected is False:
            return False
        # Any other checks to be done..? 
        # If not it would be better to just return the value of
        # chat_socket.is_connected
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
                    ["body"] = "This is the body of the message including line\n feeds"
                },
                {
                    ["title"] = "Item 2 title", 
                    ["author"] = "Konrar",
                    ["date"] = "6/29/2011",
                    ["body"] = "This is the body text\n Sometimes there are ^rColours^*"
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


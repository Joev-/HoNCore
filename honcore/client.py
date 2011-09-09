import sys, struct, socket, time, Queue
import requester, packet, deserialise, user
from exceptions import *

config_defaults = {"chatport" : 11031, "chatver" : 17, "invis" : False}

class HoNClient:    
    def __init__(self):
        self.config = config_defaults
        self.chat_socket = None
        self.bucket = Queue.Queue() # Stores exceptions

    def configure(self, *args, **kwargs):
        config_map = {
            "chatport" : self.config,
            "chatver" : self.config,
            "invis" : self.config,
            "masterserver" : requester.config,
            "basicserver" : requester.config,
            "honver" : requester.config
        }
        
        for kwarg in kwargs:
            if kwarg in config_map:
                config_map[kwarg][kwarg] = kwargs[kwarg]

    """ Account related functions. """
    def login(self, username, password):
        """ HTTP login request.
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
                response = requester.login(username, password)
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

    def logout(self):
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
                        # Force the logout and raise the error
                        user.account.logged_in = False
                        raise   # Re-raise the last exception given
                        break
                    timeout = pow(2, attempts)
                    time.sleep(timeout)
                    attempts += 1


    def is_logged_in(self):
        if user.account == None: return False
        return user.account.logged_in

    """ Chatserver related functions"""
    def chat_connect(self):
        """ Creates a socket and sends the initial authentication request to the chatserver.
            Catches the following:
                * The server responded to the authentication request.
                * The server did not respond to the authentication request.
                * Account data mismatch.
                * Connection to the server timed out.
        """
        if user.account == None or user.account.cookie == None or user.account.auth_hash == None:
            raise ChatServerError(205)
        
        self.chat_socket = packet.ChatSocket()

        try:
            self.chat_socket.connect(user.account.chat_url, self.config['chatport']) # Basic connection to the socket
        except ChatServerError:
            raise # Re-raise the exception
        
        # Send initial authentication request to the chat server.
        # If the chat server did not respond to the auth request then increment the chatver.
        attempts = 1
        while True:
            try:
                self.chat_socket.send_auth(user.account.account_id, user.account.cookie, user.account.ip, user.account.auth_hash, self.config['chatver'], self.config['invis'])
                break
            except ChatServerError, e:
                if attempts == 3:
                    self.chat_socket.connected = False # Make sure this is set.
                    if e.code == 206: # Broken Pipe, want to see the message because it's important!
                        raise
                    else:
                        raise ChatServerError(203)
                timeout = pow(2, attempts)
                time.sleep(timeout)
                attempts += 1
            
        self.chat_socket.connected = True

        # Start listening for packets from the chat server.
        listener = packet.Listener(self.chat_socket, self.bucket)
        listener.daemon = True
        listener.start()


    def chat_disconnect(self):
        """ Disconnect gracefully from the chat server and close and remove the socket."""
        if self.chat_socket:
            self.chat_socket.connected = False # Safer to stop the thread with this first.

            try:
                self.chat_socket.socket.shutdown(socket.SHUT_RDWR)
                self.chat_socket.socket.close()
            except socket.error:
                self.chat_socket = None
                raise ChatServerError(209)
            finally:
                self.chat_socket = None

    def is_connected(self):
        """ Test for chat server connection """
        try:
            exception = self.bucket.get(block=False)
        except Queue.Empty:
            if not self.chat_socket: return False
            return self.chat_socket.is_connected()
        else:
            self.chat_disconnect()
            raise exception

    """ Message of the day related functions"""

    def motd_get(self):
        """ 
        Requests the message of the day entries from the server and then pushes them through motd_parse.
        Returns a dict of motd entries.
        """
        raw = requester.motd()
        try:
            raw = deserialise.parse_raw(raw)['data']
        except ValueError:
            raise MasterServerError(108)
        return self.motd_parse(raw)

    def motd_parse(self, raw):
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
            try:
                title, body, author, date = entry.split("`")
                motd_list.append({"title" : title, "author" : author, "date" : date, "body" : body})
            except ValueError:
                raise MasterServerError(113) # Motd data error
        return motd_list


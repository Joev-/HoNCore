from exceptions import *

""" 
Functions and information for globally accessable objects, Users, Account, Channels, Buddies/Bans/Ignores. etc.
These are needed as they are global objects which are created when a response is returned from the client requester 
and will be updated in real time. The response contains a big list of buddies, bans, ignores, and other than watching for
buddy/ignore/ban add/remove packets is the only way to obtain this initial information.
"""


"""
A User object holds information pertaining a user, can be any user in HoN that the client
needs to know about. e.g. A clan member, buddy, or a user in a chat channel.

A user holds the following:
    * Nickname          The user's nickname, including the clan tag.
    * Account ID        The account ID of the user.
    * Status            The user's status. e.g. Ingame, offline, online.
    * Flags             The user's account flags. e.g. S2 admin, Prepurchased. TODO: Find out more.
    * Chat Icon         The little graphical chat icon which is usual a BR flag.
    * Nickname colour   The colour of the user's nickname.
    * Account Icon      The account icon.

Some information about users can be obtained using a whois command, the whois returns the user's status and the channels the 
user is currently in unless the user is in a game. If the user is in a game then it returns the game name and the... current
game time. e.g. "Current game time: Lobby" or "Current game time: Banning" or "Current game time: 0:39:00."
"""
class User:
    def __init__(self, nickname, account_id, status, flags, chat_icon, nick_colour, account_icon):
        self.nickname = nickname
        self.account_id = account_id
        self.status = status
        self.flags = flags
        self.chat_icon = chat_icon
        self.nick_colour = nick_colour
        self.account_icon = account_icon

    def __repr__(self):
        return "<User: #%s %s>" % (self.account_id, self.nickname)

"""
An account object holds information pertaining to the user who is logged in. It will store some account information 
which may be needed by the program. For security it should not store the password (Plus it's not needed anyway..).

What is the super_id used for, and what is the different between the super_id and account_id. Possibly the super_id is the main account
and if a sub account is purchased it is used to link to the main account? If that is the case the account_id MUST be used when performing actions. The 
super_id should only be used when a reference to the main account is needed. TODO: Find out what these are (e.g. shop stuff I guess)

"""
class Account:
    def __init__(self, super_id, account_id, nickname, cookie, auth_hash, chat_url, ip):
        self.super_id = super_id
        self.account_id = account_id
        self.nickname = nickname
        self.cookie = cookie
        self.auth_hash = auth_hash
        self.chat_url = chat_url
        self.ip = ip
        self.buddy_list = {}
        self.ban_list = {}
        self.ignore_list = {}
        self.clan_member_list = {}
        self.logged_in = False

    def __repr__(self):
        return "<User Account: #%s %s>" % (self.account_id, self.nickname)
""" 
Channel Information

Needs work and more information.

A channel holds the following
    + id        ~ The id of the channel
    + name      ~ The name of the channel
"""

class Channel:
    pass


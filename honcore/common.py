"""
HoNCore. Python library providing connectivity and functionality with HoN's chat server.

common.py

Classes for common objects, Users, Channels and Accounts.
"""

from exceptions import *


""" A User object holds information pertaining a user, this can be any user in HoN that the client
    needs to know about. e.g. A clan member, buddy, or a user in a chat channel.

    A user holds the following:
        * Nickname          The user's nickname, including the clan tag.
        * Account ID        The account ID of the user.
        * Status            The user's status. e.g. Ingame, offline, online.
        * Flags             The user's account flags. e.g. S2 admin, Prepurchased. TODO: Find out more.
        * Chat Icon         The little graphical chat icon which is usual a BR flag.
        * Nickname colour   The colour of the user's nickname.
        * Account Icon      The account icon.
"""
class User:
    def __init__(self, account_id, nickname, status=0x00, flags=0x00, chat_icon=None, nick_colour=None, account_icon=None):
        self.account_id = account_id
        self.nickname = nickname
        self.status = status
        self.flags = flags
        self.chat_icon = chat_icon
        self.nick_colour = nick_colour
        self.account_icon = account_icon

    def __repr__(self):
        return "<User: #%s %s>" % (self.account_id, self.nickname)

""" An account object holds information pertaining to the user who is logged in. 
    It will store information which has been retrieved from the master server.

    The buddy list and clan member list store only the account IDs.
    Those IDs are meant to be used to lookup the user from the clients dictionary of known users.
    From that a User object can be found, containing all of the user's information.

    The ban list and the ignore list should store a dictionary of dictionaries containing the id, 
    nickname and reason.

    TODO: What is the super_id used for, and what is the different between the super_id and account_id. 
          Possibly the super_id is the main account and if a sub account is purchased it is used to link 
          to the main account? If that is the case the account_id MUST be used when performing actions. 
          The super_id should only be used when a reference to the main account is needed.
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
        self.clan_member_list = {}
        self.ban_list = {}
        self.ignore_list = {}
        self.logged_in = False

    def __repr__(self):
        return "<User Account: #%s %s>" % (self.account_id, self.nickname)

""" A Channel object will exist for each channel that the user is in. It is created each tim the
    user joins a channel and is removed when the user leaves a channel. A list of channels that
    the user is in is stored in the client's `__channels` variable.

    The operator and user lists contain only Account IDs, the ID must be used to find either the
    user object, or the user's nickname using the clients relevant functions 
    (id_to_nick and id_to_user).

    A channel holds the following
        * ID        The ID of the channel.
        * Name      The name of the channel.
        * Topic     The topic of the channel.
        * Operators A list of operators in the channel.
        * Users     A lift of users in the channel.
"""
class Channel:
    def __init__(self, channel_id, channe_name, topic='', operators=[], users=[]):
        self.id = channel_id
        self.name = channel_name
        self.topic = topic
        self.operators = operators
        self.users = users


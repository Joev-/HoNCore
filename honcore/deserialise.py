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

from common import User, Channel, Account
from exceptions import *

from lib import phpserialize as phpd

""" Deserialises the php stuff and creates objects, not really... big... since there's this like, library... already.. """

""" 
There seems to be a difference between super_id and account_id, atleast in a trial account. 
A trial account that I created would not be able to use this program as the super_id was
different to the account id. Replacing super_id with account_id is the fix, but as to why
is a case to be solved.

If a user does not have any buddies then the buddy array is structured as follows.

buddy {
    error {
        "No buddies found" 
    }
}

If a user has a buddy then it is structured as the following.

buddy_list {
    <account_id> {
        <buddy_data_array>
    }
}

"""

def parse_raw(raw):
    """ Takes raw serialised data and returns raw non-serialised data """
    return phpd.loads(raw)

def parse(raw):
    """
    Takes raw login data and a user account, extracts useful information
    from the data and populates the account.
    """

    try:
        data = phpd.loads(raw)
    except ValueError, e:
        if e == 'unexpected opcode':
            raise MasterServerError(108)
    
    # If an auth key is found then there has been an authentication error.
    if 'auth' in data:
        raise MasterServerError(102) # Incorrect username/password
    
    """
    When the servers are down for maintenance the following array is returned
    by the master server:
        a:2{i:0,b:1,s:16:"vested_threshold",i:5;}
    See if that is true for all maintenance periods and maybe use that to consider
    when maintenance is taking place.
    """

    try:
        account = get_basic_info(data)
    except KeyError:
        raise MasterServerError(101) # Could not obtain login data

    # List of new user objects for the client to learn about.
    new_users = []


    # Note: Try/Excepts are executed quicker than if 'xx' in data statements.

    try:
        account.buddy_list, users = get_buddies(data['buddy_list'][account.account_id])
        for user in users:
            new_users.append(user)
    except KeyError:
        pass

    try:
        account.clan_member_list, users = get_clan_memebrs(data['clan_member_info'])
        for user in users:
            new_users.append(user)
    except KeyError:
        pass

    try:
        account.ban_list = get_ban_list(data['banned_list'])
    except KeyError:
        pass

    try:
        account.ignore_list = get_ignore_list(data['ignored_list'])
    except KeyError:
        pass
    
    return (account, new_users)

def get_basic_info(data):
    try:
        super_id = int(data['super_id'])
        account_id = int(data['account_id'])
        try:
            clan_tag = "[%s]" % data['clan_member_info']['tag']
        except KeyError:
            clan_tag = ''
        nickname = "%s%s" % (clan_tag, data['nickname'])
        cookie = data['cookie']
        auth_hash = data['auth_hash']
        chat_url = data['chat_url']
        ip = data['ip']
        account = Account(super_id, account_id, nickname, cookie, auth_hash, chat_url, ip)
    except KeyError, e:
        raise
    return account
    
def get_buddies(buddylist):
    """ NOTE: It is not possible to get flag or status here. """
    buddy_list = []
    new_users = []
    for userKey in buddylist:
        accid = int(buddylist[userKey]['buddy_id'])
        nick = buddylist[userKey]['nickname']
        clan_tag = buddylist[userKey]['clan_tag']
        if clan_tag:
            nick = "[%s]%s" % (clan_tag, nick)
        buddy_list.append(accid)
        new_users.append(User(accid, nick))
    return (buddy_list, new_users)

def get_ban_list(data):
    ban_list = {}
    return ban_list

def get_ignore_list(data):
    ignore_list = {}
    return ignore_list

def get_clan_memebrs(data):
    clan_members = []
    new_users = []
    return (clan_members, new_users)


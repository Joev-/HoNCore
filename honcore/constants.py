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

"""
Packet ID definitions.
Updated 23-7-11.
Client version 2.40.2
"""

""" Server -> Client """
HON_SC_AUTH_ACCEPTED			= 0x1C00
HON_SC_PING						= 0x2A00
HON_SC_CHANNEL_MSG				= 0x03
HON_SC_JOINED_CHANNEL           = 0x04
HON_SC_ENTERED_CHANNEL   		= 0x05
HON_SC_LEFT_CHANNEL     		= 0x06
HON_SC_WHISPER          		= 0x08
HON_SC_WHISPER_FAILED   		= 0x09
HON_SC_INITIAL_STATUS   		= 0x0B
HON_SC_UPDATE_STATUS    		= 0x0C
HON_SC_CLAN_MESSAGE     		= 0x13
HON_SC_LOOKING_FOR_CLAN         = 0x18
HON_SC_PM       				= 0x1C
HON_SC_PM_FAILED        		= 0x1D
HON_SC_WHISPER_BUDDIES          = 0x20
HON_SC_MAX_CHANNELS     		= 0x21
HON_SC_USER_INFO_NO_EXIST       = 0x2B
HON_SC_USER_INFO_OFFLINE        = 0x2C
HON_SC_USER_INFO_ONLINE         = 0x2D
HON_SC_USER_INFO_IN_GAME        = 0x2E
HON_SC_CHANNEL_UPDATE   		= 0x2F
HON_SC_CHANNEL_UPDATE_TOPIC     = 0x30
HON_SC_CHANNEL_KICK     		= 0x31
HON_SC_CHANNEL_BAN      		= 0x32
HON_SC_CHANNEL_UNBAN    		= 0x33
HON_SC_CHANNEL_BANNED   		= 0x34
HON_SC_CHANNEL_SILENCED         = 0x35
HON_SC_CHANNEL_SILENCE_LIFTED   = 0x36
HON_SC_CHANNEL_SILENCE_PLACED   = 0x37
HON_SC_MESSAGE_ALL      		= 0x39
HON_SC_CHANNEL_PROMOTE          = 0x3A
HON_SC_CHANNEL_DEMOTE   		= 0x3B
HON_SC_CHANNEL_AUTH_ENABLE      = 0x3E
HON_SC_CHANNEL_AUTH_DISABLE     = 0x3F
HON_SC_CHANNEL_AUTH_ADD         = 0x40
HON_SC_CHANNEL_AUTH_DELETE      = 0x41
HON_SC_CHANNEL_AUTH_LIST        = 0x42
HON_SC_CHANNEL_PASSWORD_CHANGED = 0x43
HON_SC_CHANNEL_AUTH_ADD_FAIL    = 0x44
HON_SC_CHANNEL_AUTH_DEL_FAIL    = 0x45
HON_SC_JOIN_CHANNEL_PASSWORD    = 0x46
HON_SC_CHANNEL_EMOTE    		= 0x65
HON_SC_TOTAL_ONLINE     		= 0x68
HON_SC_REQUEST_NOTIFICATION     = 0xB2
HON_SC_NOTIFICATION     		= 0xB4

""" Client -> Server """
HON_CS_PONG     				= 0x2A01
HON_CS_CHANNEL_MSG      		= 0x03
HON_CS_WHISPER          		= 0x08
HON_CS_AUTH_INFO        		= 0x0C00
HON_CS_BUDDY_ADD_NOTIFY 		= 0x0D
HON_CS_JOIN_GAME        		= 0x10
HON_CS_CLAN_MESSAGE     		= 0x13
HON_CS_PM       				= 0x1C
HON_CS_JOIN_CHANNEL     		= 0x1E
HON_CS_WHISPER_BUDDIES  		= 0x20
HON_CS_LEAVE_CHANNEL    		= 0x22
HON_CS_USER_INFO        		= 0x2A
HON_CS_UPDATE_TOPIC     		= 0x30
HON_CS_CHANNEL_KICK     		= 0x31
HON_CS_CHANNEL_BAN      		= 0x33
HON_CS_CHANNEL_UNBAN    		= 0x32
HON_CS_CHANNEL_SILENCE_USER     = 0x38
HON_CS_CHANNEL_PROMOTE          = 0x3A
HON_CS_CHANNEL_DEMOTE   		= 0x3B
HON_CS_CHANNEL_AUTH_ENABLE      = 0x3E
HON_CS_CHANNEL_AUTH_DISABLE     = 0x3F
HON_CS_CHANNEL_AUTH_ADD         = 0x40
HON_CS_CHANNEL_AUTH_DELETE      = 0x41
HON_CS_CHANNEL_AUTH_LIST        = 0x42
HON_CS_CHANNEL_SET_PASSWORD     = 0x43
HON_CS_JOIN_CHANNEL_PASSWORD    = 0x46
HON_CS_CLAN_ADD_MEMBER          = 0x47
HON_CS_CHANNEL_EMOTE    		= 0x65
HON_CS_BUDDY_ACCEPT				= 0xB3

# Dummy Events / Custom events?
HON_SC_PACKET_RECV              = "HON_SC_PACKET_RECV"

""" User Flags"""
HON_FLAGS_NONE          = 0x00
HON_FLAGS_OFFICER       = 0x01
HON_FLAGS_LEADER        = 0x02
HON_FLAGS_ADMINISTRATOR = 0x03
HON_FLAGS_STAFF         = 0x04
HON_FLAGS_PREPURCHASED  = 0x40

""" User States"""
HON_STATUS_OFFLINE      = 0
HON_STATUS_ONLINE       = 3
HON_STATUS_INLOBBY      = 4
HON_STATUS_INGAME       = 5

""" Login Modes"""
HON_MODE_NORMAL         = 0x00
HON_MODE_INVISIBLE      = 0x03


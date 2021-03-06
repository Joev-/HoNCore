#HoNCore

A python library that provides a 'client' interface to the HoN chat servers.

## About
This is a project that I worked on solely, as a way to teach myself Python over the last year. Most of the work took place between July and October before I became too busy with life and working.  
As I am no longer devloping any of my HoN projects, nor really playing HoN I would like to release them into the Public Domain and hope that others can use them to learn from and hopefully create something interesting.

## Requirements

HoNCore makes use of two additional libraries.

* [phpserialize version 1.2](http://pypi.python.org/pypi/phpserialize) - Used for deserializing the php serialized responses from the master server.
* [Construct](https://github.com/MostAwesomeDude/construct) - Used for constructing and deconstructing TCP packets.  
  * _I have been using version 2.04, I'm not sure if later versions of construct bug HoNCore, I've not tested it recently, but I have a feeling that a previous test meant that some changes needed to be made._

These libraries are in the lib folder already.

## Usage

This should really come with a setup.py, but I've not looked at those yet, sorry!
The core object used from this library is the `HoNClient` from `client.py`. Import that and create a HoNClient object to work with.

    from honcore.client import HoNClient

    client = HoNClient()

The client object has three main methods which can be used.  

###client._configure(**kwargs)  
The configure method can be used to pass configuration keys and values to the client. I'd expect any programs that use it to implement their own wrapper with `.configure()` and call `._configure()` from within that wrapper.  

Parameters:

* `basicserver` - The root server path. Default is http://heroesofnewerth.com. Needed for message of the day grabbing.
* `chatport` - The port that the chat server listens on. Default is 11031. Shouldn't change.
* `honver` - The version string for HoN. Default 2.5.7.0
* `invis` - Setting to a true value will log the user in using 'invisible' mode.
* `masterserver` - The root path to the master server. Default is http://masterserver.hon.s2games.com. Needed for all master server related functions.
* `protocol` - The chat version protocol to use. Default 21. Will need to be updated after most large patches.

###client.login(username, password)  
Logs the user in to the chat server and starts handling socket events.  

Paramters:

* `username` - A string with the user's account user name.
* `password` - A string with the md5 hash of the user's account password.
  
###client.logout()  
  Logs out from the chat server and closes any connections. Takes no parameters.

Once the user has been logged in, the client will start sending and receiving TCP packets, and handling any received ones to the registered event handlers.

I will write some documentation at a later point for those, but for now I have a very basic client example available at [BasicHoNClient](http://github.com/Joev-/basic-hon-client)

## License

_This is free and unencumbered software released into the public domain._

_Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means._

_In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law._

_THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE._

_For more information, please refer to <http://unlicense.org/>_

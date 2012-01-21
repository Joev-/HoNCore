#HoNCore

A python library that provides a 'client' interface to the HoN chat servers.

## About
This is a project that I worked on solely, as a way to teach myself Python over the last year. Most of the work took place between July and October before I became too busy with life and working.  
My main goal was to create a light-weight client that I could run on the Desktop and that project was called [HoNChatPy](http://github.com/Joev-/honchatpy.git), unfortunately that project did not really take off.  
As I am no longer devloping any of my HoN projects, nor really playing HoN I would like to release them into the Public Domain and hope that others can use them to learn from and hopefully create something interesting.

## Requirements

HoNCore makes use of two additional libraries.

* [phpserialize version 1.2](http://pypi.python.org/pypi/phpserialize) - Used for deserializing the php serialized responses from the master server.
* [Construct](https://github.com/MostAwesomeDude/construct) - Used for constructing and deconstructing TCP packets.  
  * _I have been using version 2.04, I'm not sure if later versions of construct bug HoNCore, I've not tested it recently, but I have a feeling that a previous test meant that some changes needed to be made._

## Usage

This should really come with a setup.py, but I've not looked at those yet, sorry!
The core object used from this library is the `HoNClient` from `client.py`. Import that and create a HoNClient object to work with.
```python
from honcore.client import HoNClient

client = HoNClient()
```

The client object has three main methods which can be used.  

  __client.configure()__  
    Possible configuration parameters:
    * Test
    * Test
  __client.login(username, password)__    
    Pass a username and a md5 hashed password as strings to this method to have the client log in and connect to the chat server.  
  __client.logout()__  
    Logs out from the chat server and closes any connections.  

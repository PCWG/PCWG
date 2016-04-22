# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 13:12:32 2016

@author: Stuart
"""

#class MyBroadcaster()
#    def __init__():
#        self.onChange = EventHook()
#
#theBroadcaster = MyBroadcaster()
#
## add a listener to the event
#theBroadcaster.onChange += myFunction
#
## remove listener from the event
#theBroadcaster.onChange -= myFunction
#
## fire event
#theBroadcaster.onChange.fire()

class EventHook(object):

    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        for handler in self.__handlers:
            handler(*args, **keywargs)

    def clearObjectHandlers(self, inObject):
        for theHandler in self.__handlers:
            if theHandler.im_self == inObject:
                self -= theHandler


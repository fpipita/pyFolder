# -*- coding: utf-8 -*-



from Notifier import *



## A default Notifier that does nothing.

class NullNotifier (Notifier):



    def __init__ (self, pyFolder):
        Notifier.__init__ (self, pyFolder)



    def info (self, title, text):
        pass



    def warning (self, title, text):
        pass



    def error (self, title, text):
        pass

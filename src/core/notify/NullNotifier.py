# -*- coding: utf-8 -*-



from Notifier import *



## A default Notifier that does nothing.

class NullNotifier (Notifier):



    def notify (self, title, text):
        pass



    def warning (self, title, text):
        pass



    def error (self, title, text):
        pass

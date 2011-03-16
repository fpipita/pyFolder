from Notifier import *



class NullNotifier (Notifier):



    ## A default Notifier that does nothing.

    def notify (self, event, *args):
        pass

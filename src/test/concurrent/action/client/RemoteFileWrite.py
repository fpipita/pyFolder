# -*- coding: utf-8 -*-



from ClientAction import *



class RemoteFileWrite (ClientAction):



    def __init__ (self, User, pyFolder, **kwargs):
        ClientAction.__init__ (self, User, pyFolder, **kwargs)

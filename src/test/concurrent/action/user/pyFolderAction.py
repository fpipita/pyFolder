# -*- coding: utf-8 -*-



import sys



sys.path.append ('../')



from action.Action import *



class pyFolderAction (Action):



    def __init__ (self, User, pyFolder, **kwargs):
        Action.__init__ (self, User, pyFolder, **kwargs)
        self.Responses = []
        self.action = None



    def execute (self):
        self.Responses = self.action ()



    def can_happen (self):
        return True



    def __repr__ (self):
        return '{0}'.format (self.__class__.__name__)

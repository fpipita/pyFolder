# -*- coding: utf-8 -*-



from Action import *



class pyFolderAction (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)
        self.Responses = []
        self.action = None



    def execute (self):
        self.Responses = self.action ()



    def can_happen (self):
        return True

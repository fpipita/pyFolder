# -*- coding: utf-8 -*-



from Action import *



class Commit (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.commit ()



    def can_happen (self):
        return True

# -*- coding: utf-8 -*-



from Action import *



class DeleteDirectory (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        pass



    def can_happen (self):
        return False

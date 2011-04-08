# -*- coding: utf-8 -*-



from Action import *



class DeleteFile (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        pass



    def can_happen (self):
        return False

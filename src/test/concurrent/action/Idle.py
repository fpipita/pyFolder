# -*- coding: utf-8 -*-



from Action import *



## The user does nothing.

class Idle (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        print 'User {0} : Idle'.format (self.User)



    def can_happen (self):
        return True

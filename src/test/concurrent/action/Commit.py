# -*- coding: utf-8 -*-



from Action import *



class Commit (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.commit ()
        print 'User {0} : Commit executed'.format (self.User)



    def can_happen (self):
        return True

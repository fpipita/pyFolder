# -*- coding: utf-8 -*-



from Action import *



class Update (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.update ()
        print 'User {0} : Update executed'.format (self.User)



    def can_happen (self):
        return True

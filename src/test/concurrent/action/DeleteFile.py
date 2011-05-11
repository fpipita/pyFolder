# -*- coding: utf-8 -*-



from Action import *
from rand.PathFactory import *



class DeleteFile (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.delete (self.Target)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        self.Target = PathFactory.select_path (self.pyFolder)

        return self.Target is not None

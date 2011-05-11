# -*- coding: utf-8 -*-



from Action import *
from rand.PathFactory import *



class DeleteDirectory (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.rmdir (self.Target)



    def can_happen (self):

        if not len (self.pyFolder.get_directories (ExcludeiFolders=True)):
            return False

        self.Target = PathFactory.select_path (self.pyFolder, isdir=True)

        return self.Target is not None

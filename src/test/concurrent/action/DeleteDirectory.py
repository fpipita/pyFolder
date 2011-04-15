# -*- coding: utf-8 -*-



from Action import *
from rand.PathFactory import *



class DeleteDirectory (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.rmdir (self.ActionData['Path'])



    def can_happen (self):

        if not len (self.pyFolder.get_directories (ExcludeiFolders=True)):
            return False

        self.ActionData['Path'] = \
            PathFactory.select_path (self.pyFolder, isdir=True)

        return self.ActionData['Path'] is not None

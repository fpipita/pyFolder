# -*- coding: utf-8 -*-



from UserAction import *
from rand.PathFactory import *



class DeleteDirectory (UserAction):



    def __init__ (self, User, pyFolder):
        UserAction.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.rmdir (self.Target)



    def can_happen (self):

        if not len (self.pyFolder.get_directories (ExcludeiFolders=True)):
            return False

        return self.Target is not None



    def build_scenario (self):
        self.Target = PathFactory.select_path (self.pyFolder, isdir=True)

        Scenario = []

        return Scenario

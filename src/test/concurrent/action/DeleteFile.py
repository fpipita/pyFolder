# -*- coding: utf-8 -*-



from UserAction import *
from rand.PathFactory import *



class DeleteFile (UserAction):



    def __init__ (self, User, pyFolder):
        UserAction.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.delete (self.Target)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        return self.Target is not None



    def build_scenario (self):
        self.Target = PathFactory.select_path (self.pyFolder)

        Scenario = []

        return Scenario

# -*- coding: utf-8 -*-



from UserAction import *
from common.constants import *
from rand.PathFactory import *



## Create a random file

class CreateFile (UserAction):



    def __init__ (self, User, pyFolder):
        UserAction.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.touch (self.Target)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        return len (self.Target) < MAX_PATH



    def build_scenario (self):
        self.Target = PathFactory.create_path (self.pyFolder)

        Scenario = []

        return Scenario

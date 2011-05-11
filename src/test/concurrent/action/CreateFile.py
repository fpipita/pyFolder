# -*- coding: utf-8 -*-



from Action import *
from common.constants import *
from rand.PathFactory import *



## Create a random file

class CreateFile (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        self.pyFolder.touch (self.Target)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        self.Target = PathFactory.create_path (self.pyFolder)

        return len (self.Target) < MAX_PATH

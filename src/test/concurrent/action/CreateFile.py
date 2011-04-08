# -*- coding: utf-8 -*-



import sys



sys.path.append ('../')



from Action import *
from common.constants import *
from rand.PathFactory import *



## Create a random file

class CreateFile (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)
        self.ActionData['Path'] = None



    def execute (self):
        self.pyFolder.touch (self.ActionData['Path'])



    def can_happen (self):
        
        if not len (self.pyFolder.get_directories ()):
            return False
        
        self.ActionData['Path'] = PathFactory.create_path (self.pyFolder)

        return len (self.ActionData['Path']) < MAX_PATH

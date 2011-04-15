# -*- coding: utf-8 -*-



import sys



sys.path.append ('../')



from Action import *
from common.constants import *
from rand.PathFactory import *
from rand.DataGenerator import *



## Modify an existing file

class ModifyFile (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        RandomData = DataGenerator.generate (MIN_FILE_SIZE, MAX_FILE_SIZE)
        self.pyFolder.write_file (self.ActionData['Path'], RandomData)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        self.ActionData['Path'] = PathFactory.select_path (self.pyFolder)

        return self.ActionData['Path'] is not None

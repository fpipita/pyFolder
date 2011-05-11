# -*- coding: utf-8 -*-



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
        self.pyFolder.write_file (self.Target, RandomData)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        self.Target = PathFactory.select_path (self.pyFolder)

        return self.Target is not None

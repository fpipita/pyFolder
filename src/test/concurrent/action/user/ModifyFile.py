# -*- coding: utf-8 -*-



from UserAction import *
from common.constants import *
from rand.PathFactory import *
from rand.DataGenerator import *



## Modify an existing file

class ModifyFile (UserAction):



    def __init__ (self, User, pyFolder):
        UserAction.__init__ (self, User, pyFolder)



    def execute (self):
        RandomData = DataGenerator.generate (MIN_FILE_SIZE, MAX_FILE_SIZE)
        self.pyFolder.write_file (self.Target, RandomData)



    def can_happen (self):

        if not len (self.pyFolder.get_directories ()):
            return False

        return self.Target is not None



    def build_scenario (self):
        self.Target = PathFactory.select_path (self.pyFolder)

        Scenario = []

        return Scenario

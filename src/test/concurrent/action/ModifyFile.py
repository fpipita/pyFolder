# -*- coding: utf-8 -*-



import sys



sys.path.append ('../')



from Action import *
from common.constants import *
from rand.PathFactory import *



## Modify an existing file

class ModifyFile (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        pass



    def can_happen (self):
        return False

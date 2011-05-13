# -*- coding: utf-8 -*-



import random



from Action import *
from common.constants import *
from rand.PathFactory import *



KEEP_EXISTING = 0
KEEP_NEW = 1



# Simulates an user who has found a conflicted entry in his
# local iFolder and has to chose whether to keep its copy (by renaming
# it and overwriting the fresh added one) or to accept the new one

class HandleConflict (Action):



    def __init__ (self, User, pyFolder):
        Action.__init__ (self, User, pyFolder)



    def execute (self):
        Choice = random.randint (KEEP_EXISTING, KEEP_NEW)
        OriginalPath = self.pyFolder.strip_conflicted_suffix (self.Target)

        DeleteTarget = None
        DeleteOriginal = None

        if self.pyFolder.path_isfile (OriginalPath):
            DeleteOriginal = self.pyFolder.delete

        elif self.pyFolder.path_isdir (OriginalPath):
            DeleteOriginal = self.pyFolder.rmdir

        if self.pyFolder.path_isfile (self.Target):
            DeleteTarget = self.pyFolder.delete

        elif self.pyFolder.path_isdir (self.Target):
            DeleteTarget = self.pyFolder.rmdir

        if Choice == KEEP_EXISTING:
            print 'KEEP EXISTING {0}'.format (self.Target)

            if self.pyFolder.path_exists (OriginalPath):
                DeleteOriginal (OriginalPath)

            self.pyFolder.rename (self.Target, OriginalPath)

        elif Choice == KEEP_NEW:
            print 'KEEP NEW {0}'.format (OriginalPath)
            DeleteTarget (self.Target)



    def can_happen (self):
        self.Target = PathFactory.select_conflicted_path (self.pyFolder)

        return self.Target is not None

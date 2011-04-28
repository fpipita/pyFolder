# -*- coding: utf-8 -*-



from pyFolderAction import *



class Update (pyFolderAction):



    def __init__ (self, User, pyFolder):
        pyFolderAction.__init__ (self, User, pyFolder)
        self.action = self.pyFolder.update

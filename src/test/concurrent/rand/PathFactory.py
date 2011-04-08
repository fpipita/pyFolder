# -*- coding: utf-8 -*-



import os
import random
import sys



sys.path.append ('../')



from common.constants import *



class PathFactory:



    @staticmethod
    def create_path (pyFolder, isdir=False):

        Path = None

        while True:
            Parent = PathFactory.select_parent (pyFolder)
            Name = PathFactory.create_name ()

            Path = os.path.join (Parent, Name)


            if isdir:
                if not pyFolder.path_isdir (Path):
                    break
            
            else:
                if not pyFolder.path_isfile (Path):
                    break

        return Path



    @staticmethod
    def select_parent (pyFolder):
        Tree = pyFolder.get_directories ()
        return random.choice (Tree)



    @staticmethod
    def create_name ():
        Length = random.randint (MIN_NAME_LENGTH, MAX_NAME_LENGTH)
        CharList = random.sample (ALPHABETH, Length)

        Name = str ()

        for Char in CharList:
            Name += Char

        return Name

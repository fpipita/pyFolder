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



    ## Select an existing random path from the pyFolder repository.
    #
    #  @param isdir If True, select a random directory, else a random
    #               file.
    #
    #  @return A random existing path or None if no paths are available.

    @staticmethod
    def select_path (pyFolder, isdir=False):

        Tree = None

        if isdir:
            Tree = pyFolder.get_directories (ExcludeiFolders=True)

        else:
            Tree = pyFolder.get_files ()

        if len (Tree):
            return random.choice (Tree)

        return None



    @staticmethod
    def select_conflicted_path (pyFolder):

        ConflictedEntries = pyFolder.get_conflicted_entries ()

        if not len (ConflictedEntries):
            return None

        return random.choice (ConflictedEntries)

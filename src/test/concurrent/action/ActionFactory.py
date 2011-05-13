# -*- coding: utf-8 -*-



import random



from Idle import *
from Commit import *
from Update import *
from CreateDirectory import *
from CreateFile import *
from DeleteDirectory import *
from DeleteFile import *
from ModifyFile import *
from HandleConflict import *



class ActionFactory:



    Actions = {
        'Idle' : Idle,
        'Commit' : Commit,
        'Update' : Update,
        'CreateDirectory' : CreateDirectory,
        'CreateFile' : CreateFile,
        'DeleteDirectory' : DeleteDirectory,
        'DeleteFile' : DeleteFile,
        'ModifyFile' : ModifyFile,
        'HandleConflict' : HandleConflict
        }



    @staticmethod
    def create (User, pyFolder):

        Keys = ActionFactory.Actions.keys ()
        RandomKey = random.choice (Keys)
        Action = ActionFactory.Actions[RandomKey] (User, pyFolder)

        if Action.can_happen ():
            return Action

        return ActionFactory.Actions['Idle'] (User, pyFolder)

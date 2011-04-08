# -*- coding: utf-8 -*-



import random



from Idle import *
from Commit import *
from Update import *
from CreateDirectory import *
from CreateFile import *
from DeleteDirectory import *
from DeleteFile import *



class ActionFactory:



    Actions = {
        'Idle' : Idle,
        'Commit' : Commit,
        'Update' : Update,
        'CreateDirectory' : CreateDirectory,
        'CreateFile' : CreateFile,
        'DeleteDirectory' : DeleteDirectory,
        'DeleteFile' : DeleteFile
        }



    @staticmethod
    def create (User, pyFolder):

        Keys = ActionFactory.Actions.keys ()
        Action = ActionFactory.Actions[random.choice (Keys)] (User, pyFolder)

        if Action.can_happen ():
            return Action

        return ActionFactory.Actions['Idle'] (User, pyFolder)

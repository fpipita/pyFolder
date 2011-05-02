# -*- coding: utf-8 -*-



import random



from Idle import *

from user.Commit import *
from user.Update import *
from user.CreateDirectory import *
from user.CreateFile import *
from user.DeleteDirectory import *
from user.DeleteFile import *
from user.ModifyFile import *
from client.RemoteMkdir import *
from client.RenameOnNameConflict import *
from client.RenameOnInvalidChars import *
from client.IgnoreLockedEntry import *
from client.Rollback import *
from client.IgnoreForbiddenEntry import *


class ActionFactory:



    UserActions = {
        'Idle' : Idle,
        'Commit' : Commit,
        'Update' : Update,
        'CreateDirectory' : CreateDirectory,
        # 'CreateFile' : CreateFile,
        # 'DeleteDirectory' : DeleteDirectory,
        # 'DeleteFile' : DeleteFile,
        # 'ModifyFile' : ModifyFile
        }

    ClientActions = {
        'RemoteMkdir' : RemoteMkdir,
        'RenameOnNameConflict' : RenameOnNameConflict,
        'RenameOnInvalidChars' : RenameOnInvalidChars,
        'IgnoreLockedEntry' : IgnoreLockedEntry,
        'Rollback' : Rollback,
        'IgnoreForbiddenEntry' : IgnoreForbiddenEntry
        }



    @staticmethod
    def create_random_user_action (User, pyFolder):

        Keys = ActionFactory.UserActions.keys ()
        RandomKey = random.choice (Keys)
        Action = ActionFactory.UserActions[RandomKey] (User, pyFolder)

        if Action.can_happen ():
            return Action

        return ActionFactory.UserActions['Idle'] (User, pyFolder)



    @staticmethod
    def create_client_action (User, pyFolder, **kwargs):

        if 'Action' not in kwargs or 'Target' not in kwargs:
            return ActionFactory.UserActions['Idle'] (
                User, pyFolder)

        return ActionFactory.ClientActions[kwargs['Action']] (
            User, pyFolder, **kwargs)



    @staticmethod
    def create_scenario (User, pyFolder, Target, ActionList):
        Scenario = []

        for Action in ActionList:
            Scenario.append (
                ActionFactory.create_client_action (
                    User, pyFolder, Action=Action, Target=Target))

        return Scenario

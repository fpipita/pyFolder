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
from client.RemoteCreateFile import *
from client.ClientIdle import *



class ActionFactory:



    UserActions = {
        'Idle' : Idle,
        'Commit' : Commit,
        'Update' : Update,
        'CreateDirectory' : CreateDirectory,
        'CreateFile' : CreateFile
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
        'IgnoreForbiddenEntry' : IgnoreForbiddenEntry,
        'RemoteCreateFile' : RemoteCreateFile,
        'ClientIdle' : ClientIdle
        }



    @staticmethod
    def create_random_user_action (User, pyFolder):

        Keys = ActionFactory.UserActions.keys ()
        RandomKey = random.choice (Keys)
        Action = ActionFactory.UserActions[RandomKey] (User, pyFolder)

        if Action.can_happen ():

            if isinstance (Action, UserAction):
                ClientIdle = ActionFactory.create_client_action (
                    User,
                    pyFolder,
                    Action='ClientIdle',
                    Target=Action.Target)

                Action.ClientIdle = ClientIdle

            return Action

        return ActionFactory.UserActions['Idle'] (User, pyFolder)



    @staticmethod
    def create_client_action (User, pyFolder, **kwargs):
        return ActionFactory.ClientActions[kwargs['Action']] (
            User, pyFolder, **kwargs)



    @staticmethod
    def create_scenario (User, pyFolder, Target, ActionList):
        Scenario = []

        for Action in ActionList:

            ExecutedAction = ActionFactory.create_client_action (
                User,
                pyFolder,
                Action=Action,
                Target=Target)

            Scenario.append (ExecutedAction)

        return Scenario

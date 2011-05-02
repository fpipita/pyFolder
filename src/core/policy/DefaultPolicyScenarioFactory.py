# -*- coding: utf-8 -*-



from ScenarioFactory import *



class DefaultPolicyScenarioFactory (ScenarioFactory):



    def __init__ (self, ActionFactory):
        ScenarioFactory.__init__ (self, ActionFactory)



    def create_directory (self, UserAction):
        ClientResponses = [
            'RemoteMkdir',
            'RenameOnNameConflict',
            'RenameOnInvalidChars',
            'IgnoreLockedEntry',
            'Rollback',
            'IgnoreForbiddenEntry',
            'ClientIdle'
            ]

        return self.ActionFactory.create_scenario (
            UserAction.User,
            UserAction.pyFolder,
            UserAction.Target,
            ClientResponses)



    def create_file (self, UserAction):
        ClientResponses = [
            'RemoteCreateFile',
            'RenameOnNameConflict',
            'RenameOnInvalidChars',
            'IgnoreLockedEntry',
            'Rollback',
            'IgnoreForbiddenEntry',
            'ClientIdle'
            ]

        return self.ActionFactory.create_scenario (
            UserAction.User,
            UserAction.pyFolder,
            UserAction.Target,
            ClientResponses)



    def delete_directory (self, UserAction):
        raise NotImplementedError



    def delete_file (self, UserAction):
        raise NotImplementedError



    def modify_file (self, UserAction):
        raise NotImplementedError

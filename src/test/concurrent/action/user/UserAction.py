# -*- coding: utf-8 -*-



import sys



sys.path.append ('../')
sys.path.append ('../../')



from action.Action import *



class UserAction (Action):



    def __init__ (self, User, pyFolder, **kwargs):
        Action.__init__ (self, User, pyFolder, **kwargs)
        self.Target = None
        self.ClientIdle = None
        self.Scenario = self.build_scenario ()



    def find_response (self, ClientActionList):

        # `Scenario' is a list of the possible actions done by pyFolder, 
        # in response to the execution of the current user action. Each
        # class that inherits from UserAction, should build its own scenario,
        # by redefining the build_scenario abstract method.

        for PossibleAction in self.Scenario:

            if PossibleAction in ClientActionList:
                ClientActionList.remove (PossibleAction)
                return PossibleAction

        if self.ClientIdle in self.Scenario:
            return self.ClientIdle

        return None



    def build_scenario (self):
        raise NotImplementedError



    def __repr__ (self):
        return '{0} `{1}\''.format (self.__class__.__name__, self.Target)

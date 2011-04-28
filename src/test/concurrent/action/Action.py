# -*- coding: utf-8 -*-



## Abstract base class for the actions.

class Action:



    def __init__ (self, User, pyFolder):
        self.User = User
        self.pyFolder = pyFolder



    ## Execute the current action.

    def execute (self):
        raise NotImplementedError



    ## Check whether the current action can happen or not.
    #
    #  @return True if the action can happen within the current
    #          context.

    def can_happen (self):
        raise NotImplementedError

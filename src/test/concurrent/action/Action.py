# -*- coding: utf-8 -*-



class Action:



    def __init__ (self, User, pyFolder):
        self.ActionData = {}
        self.User = User
        self.pyFolder = pyFolder



    def execute (self):
        raise NotImplementedError



    def can_happen (self):
        raise NotImplementedError

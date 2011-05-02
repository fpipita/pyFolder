# -*- coding: utf-8 -*-



class ScenarioFactory:



    def __init__ (self, ActionFactory):
        self.ActionFactory = ActionFactory



    def create_directory (self, UserAction):
        raise NotImplementedError



    def create_file (self, UserAction):
        raise NotImplementedError



    def delete_directory (self, UserAction):
        raise NotImplementedError



    def delete_file (self, UserAction):
        raise NotImplementedError



    def modify_file (self, UserAction):
        raise NotImplementedError

# -*- coding: utf-8 -*-



from Policy import *
from DefaultPolicy import *



class PolicyFactory:



    @staticmethod
    def create (policy, pyFolder):
        return DefaultPolicy (pyFolder)
    


    @staticmethod
    def get_factories ():
        return ['DefaultPolicy', ]

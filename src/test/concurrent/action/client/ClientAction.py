# -*- coding: utf-8 -*-



import sys



sys.path.append ('../')



from action.Action import *



class ClientAction (Action):



    def __init__ (self, User, pyFolder, **kwargs):
        Action.__init__ (self, User, pyFolder, **kwargs)
        self.Target = kwargs['Target']



    def execute (self):
        pass



    def can_happen (self):
        return True



    def __eq__ (self, other):
        return isinstance (other, self.__class__) and \
            self.Target == other.Target



    def __ne__ (self, other):
        return not isinstance (other, self.__class__) or \
            self.Target != other.Target



    def __repr__ (self):
        return '{0} `{1}\''.format (self.__class__.__name__, self.Target)

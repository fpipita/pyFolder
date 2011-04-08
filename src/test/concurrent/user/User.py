# -*- coding: utf-8 -*-


from threading import *
import random
import sys
import time



sys.path.append ('../')
sys.path.append ('../../')



from common.constants import *
from action.ActionFactory import *
from core.config import ConfigManager
from pyFolder import *



class User (Thread):
    
    
    
    def __init__ (self, ActionHistory, Errors, **kwargs):

        Thread.__init__ (self)
        self.ActionHistory = ActionHistory
        self.Errors = Errors
        self.USERDATA = kwargs



    def run (self):

        # Create the pyFolder instance owned by the user here (to avoid
        # the SQLite concurrent error).

        cm = ConfigManager (runfromtest=True, **self.USERDATA)
        self.pyFolder = pyFolder (cm, runfromtest=True)

        self.pyFolder.checkout ()
        
        while True:

            Action = ActionFactory.create (self, self.pyFolder)

            try:

                Action.execute ()
                self.ActionHistory.put (Action)

            except Exception:

                self.Errors.put (Action)

            time.sleep (random.randint (MIN_WAIT_TIME, MAX_WAIT_TIME))

            
    def __repr__ (self):
        return '{0}'.format (self.USERDATA['username'])

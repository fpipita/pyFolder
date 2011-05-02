# -*- coding: utf-8 -*-



from threading import *
import random
import sys
import time



sys.path.append ('../')
sys.path.append ('../../')



from common.constants import *
from action.ActionFactory import *
from action.user.pyFolderAction import *
from action.user.UserAction import *
from core.config import ConfigManager
from pyFolder import *



class User (Thread):
    
    
    
    def __init__ (self, ActionHistory, Errors, **kwargs):

        Thread.__init__ (self)
        self.ActionHistory = ActionHistory
        self.Errors = Errors
        self.USERDATA = kwargs
        self.IsRunning = True
        self.lock = Lock ()



    def __is_running (self):
        Retval = None

        with self.lock:
            Retval = self.IsRunning

        return Retval



    def stop (self):

        with self.lock:
            self.IsRunning = False

        self.join ()



    def run (self):

        # Create the pyFolder instance owned by the user here (to avoid
        # the SQLite concurrent error).

        cm = ConfigManager (runfromtest=True, **self.USERDATA)
        self.pyFolder = pyFolder (
            cm, runfromtest=True, ActionFactory=ActionFactory)

        self.pyFolder.checkout ()

        Queue = []

        while self.__is_running ():
            Action = ActionFactory.create_random_user_action (
                self, self.pyFolder)

            try:
                Action.execute ()

                if isinstance (Action, pyFolderAction):
                    self.ActionHistory.put ((Action, Queue))
                    Queue = []

                else:

                    if isinstance (Action, UserAction):
                        Queue.append (Action)

            except Exception:
                self.Errors.put (Action)

            time.sleep (random.randint (MIN_WAIT_TIME, MAX_WAIT_TIME))

            
    def __repr__ (self):
        return '{0}'.format (self.USERDATA['username'])

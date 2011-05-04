# -*- coding: utf-8 -*-



from threading import *
import inspect
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



DEBUG_STR = 'user={0}, exception={1}, action={2}, ' \
    'user_actions={3}, client_responses={4}'



class User (Thread):



    def __init__ (self, Errors, **kwargs):

        Thread.__init__ (self)
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

                print '* User {0} -> {1}'.format (self, Action)

                Action.execute ()

                if isinstance (Action, pyFolderAction):
                    ClientActions = Action.Responses

                    for ExecutedAction in Queue:
                        assert ExecutedAction.find_response (
                            ClientActions) is not None

                    Queue = []

                else:

                    if isinstance (Action, UserAction):
                        Queue.append (Action)

            except Exception, ex:
                print DEBUG_STR.format (
                    self, ex, Action, Queue, Action.Responses)

                print '*' * 80

                Trace = inspect.trace ()

                for x in Trace:
                    print x[1:]

                self.Errors.put ((Action, Trace))

            time.sleep (random.randint (MIN_WAIT_TIME, MAX_WAIT_TIME))



    def __repr__ (self):
        return '{0}'.format (self.USERDATA['username'])

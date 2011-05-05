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



EXCEPTION_MSG = 'User={0}\nException={1}\nAction={2}\n' \
    'UserActions={3}\nClientResponses={4}'
INFO_MSG = '* {0}.{1} ({2})={3} [ {4} ]'



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

#                print '* User {0} -> {1}'.format (self, Action)

                Action.execute ()

                if isinstance (Action, pyFolderAction):
                    ClientActions = Action.Responses

                    for ExecutedAction in Queue:
                        Response = ExecutedAction.find_response (
                            ClientActions)

                        print INFO_MSG.format (
                            self,
                            Action,
                            ExecutedAction,
                            Response,
                            {True : 'OK', False : 'FAIL'}[Response is not None])

                    Queue = []

                else:

                    if isinstance (Action, UserAction):
                        Queue.append (Action)

            except Exception, ex:
                print '*' * 80

                print EXCEPTION_MSG.format (
                    self, ex, Action, Queue, Action.Responses)

                Trace = inspect.trace ()

                print '- StackTrace follows'

                for x in Trace:
                    print x[1:]

                self.Errors.put ((Action, Trace))

                print '*' * 80

            time.sleep (random.randint (MIN_WAIT_TIME, MAX_WAIT_TIME))



    def __repr__ (self):
        return '{0}'.format (self.USERDATA['username'])

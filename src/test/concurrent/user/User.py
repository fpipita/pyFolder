# -*- coding: utf-8 -*-



from threading import *
import datetime
import inspect
import random
import sys
import time



sys.path.append ('../')
sys.path.append ('../../')



from common.constants import *
from action.ActionFactory import *
from core.config import ConfigManager
from pyFolder import *



MAX_VALUES_LENGTH = 199
TRACE_MSG = '[ {1} ] In file `{3}\', lineno {4}, function `{5}\', code `{0}\'' \
    '\nArgvalues={2}'



def formatvalue (value):

    try:
        return '={0}'.format (value[:MAX_VALUE_LENGTH])

    except:
        return '={0}'.format (value)



class User (Thread):



    def __init__ (self, **kwargs):

        Thread.__init__ (self)
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
        self.pyFolder = pyFolder (cm, runmode=RUN_AS_OBJECT)

        self.pyFolder.checkout ()

        while self.__is_running ():
            Action = ActionFactory.create (self, self.pyFolder)

            try:

                Action.execute ()

            except Exception, ex:
                print '*' * 80

                now = datetime.datetime.now ().isoformat ()

                print 'Exception of type `{0}\' : {1}'.format (type (ex), ex)

                Trace = inspect.trace ()

                for Frame in Trace:
                    print '-' * 80

                    argvalues = inspect.formatargvalues (
                    *inspect.getargvalues (Frame[0]),
                     formatvalue=formatvalue)

                    print TRACE_MSG.format (
                        Frame[4][Frame[5]].strip (),
                        now,
                        argvalues,
                        *Frame[1:4])

                print '*' * 80

            time.sleep (random.randint (MIN_WAIT_TIME, MAX_WAIT_TIME))



    def __repr__ (self):
        return '{0}'.format (self.USERDATA['username'])

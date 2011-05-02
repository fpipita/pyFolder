# -*- coding: utf-8 -*-



import os
import Queue
import shutil
import sys
import time



sys.path.append ('../')



from common.constants import *
from setup import *
from user.User import *



TEST_CONFIG = Setup ('../setup.ini')



# Each item of those Queues, is a tuple : (pyFolderAction, list<UserAction>).

ActionHistory = Queue.Queue ()
Errors = Queue.Queue ()



def load_users ():

    UserList = []

    for Key in TEST_CONFIG.USERDATA.keys ():
        UserList.append (User (ActionHistory, Errors, **TEST_CONFIG.USERDATA[Key]))

    return UserList



def stop_simulation (UserList):

    print 'Please, wait until all the threads are being shutted down.'

    for User in UserList:
        User.stop ()
        shutil.rmtree (User.USERDATA['prefix'])



if __name__ == '__main__':

    UserList = load_users ()

    for User in UserList:
        os.makedirs (User.USERDATA['prefix'])
        User.start ()

    raw_input ('Press the Enter key to end the simulation.')

    stop_simulation (UserList)

    while not ActionHistory.empty ():
        Scenario = ActionHistory.get ()

        ClientActions = Scenario[0].Responses

        UserActions = Scenario[1]

        for UserAction in UserActions:
            print 'The user {0}, executed \"{1}\" and ' \
                'the client responded with \"{2}\"'.format (
                UserAction.User,
                UserAction,
                UserAction.find_response (ClientActions))

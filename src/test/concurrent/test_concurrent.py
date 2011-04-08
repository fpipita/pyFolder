# -*- coding: utf-8 -*-



import os
import Queue
import shutil
import sys



sys.path.append ('../')



from common.constants import *
from setup import *
from user.User import *



TEST_CONFIG = Setup ('../setup.ini')
CommandHistory = Queue.Queue ()
Errors = Queue.Queue ()



def load_users ():

    UserList = []

    for Key in TEST_CONFIG.USERDATA.keys ():
        UserList.append (User (CommandHistory, Errors, **TEST_CONFIG.USERDATA[Key]))

    return UserList



if __name__ == '__main__':

    Users = load_users ()
    for User in Users:
        os.makedirs (User.USERDATA['prefix'])
        User.start ()

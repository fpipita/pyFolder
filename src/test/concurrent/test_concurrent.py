#!/usr/bin/python
# -*- coding: utf-8 -*-



import os
import shutil
import sys
import time



sys.path.append ('../')



from common.constants import *
from setup import *
from user.User import *



TEST_CONFIG = Setup ('../setup.ini')



def load_users ():

    UserList = []

    for Key in TEST_CONFIG.USERDATA.keys ():
        UserList.append (User (**TEST_CONFIG.USERDATA[Key]))

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

    raw_input ('Press the Enter key to end the simulation.\n')

    stop_simulation (UserList)

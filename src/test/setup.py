# -*- coding: utf-8 -*-

import ConfigParser
import os
import sys

class Setup:
    def __init__ (self):
        self.SETUP_INI = 'setup.ini'
        self.WAIT_FOR_SIMIAS_TO_UPDATE = 5

        self.USERDATA_A = {\
            'username': lambda p: p, \
                'password': lambda p: p, \
                'ifolderws': lambda p: p, \
                'pathtodb': lambda p: os.path.join (self.__dict__['USERDATA_A']['prefix'], p), \
                'soapbuflen': lambda p: int (p), \
                'prefix': lambda p: p, \
                'config': lambda p: os.path.join (self.__dict__['USERDATA_A']['prefix'], p), \
                'policy': lambda p: p, \
                'verbose': lambda p: p == 'True' \
            }

        self.USERDATA_B = {\
            'username': lambda p: p, \
                'password': lambda p: p, \
                'ifolderws': lambda p: p, \
                'pathtodb': lambda p: os.path.join (self.__dict__['USERDATA_B']['prefix'], p), \
                'soapbuflen': lambda p: int (p), \
                'prefix': lambda p: p, \
                'config': lambda p: os.path.join (self.__dict__['USERDATA_B']['prefix'], p), \
                'policy': lambda p: p, \
                'verbose': lambda p: p == 'True' \
            }

        self.load_configuration ()

    def load_configuration (self):
        if os.path.isfile (self.SETUP_INI):
            config = ConfigParser.RawConfigParser ()
            config.read (self.SETUP_INI)
            
            USERDATA = ['USERDATA_A', 'USERDATA_B']

            for USER in USERDATA:
                if config.has_section (USER):
                    keys = self.__dict__[USER].keys ()
                    keys.insert (0, keys.pop (keys.index ('prefix')))
                    for key in keys:
                        if config.has_option (USER, key):
                            try:
                                self.__dict__[USER][key] = self.__dict__[USER][key] (config.get (USER, key))
                            except Exception, e:
                                print >> sys.stderr, e
                                sys.exit ()
                        else:
                            print >> sys.stderr, \
                                'Error : could not find ' \
                                'configuration parameter `{0}\' in ' \
                                'section `{1}\'. Aborting.'.format (key, USER)
                            sys.exit ()
                else:
                    print >> sys.stderr, \
                        'Error : could not find ' \
                        'configuration section `{0}\'. ' \
                        'Aborting.'.format (USER)
                    sys.exit ()
                    
            if os.path.exists (self.USERDATA_A['prefix']) or \
                    self.USERDATA_A['prefix'] == '':
                print >> sys.stderr, 'ERROR: the `prefix\' setting in the',
                print >> sys.stderr, '`USERDATA_A\' section can\'t be an',
                print >> sys.stderr, 'already existing path or empty.',
                print >> sys.stderr, 'Aborting.'
                sys.exit ()

            if config.has_section ('Options'):
                if config.has_option ('Options', 'SIMIAS_REFRESH'):
                    try:
                        self.WAIT_FOR_SIMIAS_TO_UPDATE = \
                            config.getfloat ('Options', 'SIMIAS_REFRESH')
                    except ConfigParser.Error:
                        print >> sys.stderr, \
                        'Warning : The SIMIAS_REFRESH option ' \
                        'does not contain a valid value, defaulting ' \
                        'to {0} seconds'.format (\
                            self.WAIT_FOR_SIMIAS_TO_UPDATE)
        else:
            print >> sys.stderr, \
                'Error : could not read the ' \
                'configuration file `{0}\'. ' \
                'Aborting.'.format (self.SETUP_INI)
            sys.exit ()

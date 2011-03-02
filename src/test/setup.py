# -*- coding: utf-8 -*-

import ConfigParser
import os
import sys

class Setup:
    SETUP_INI = 'setup.ini'

    USERDATA_A = {\
        'username':'', \
            'password':'', \
            'ifolderws':'', \
            'pathtodb':'', \
            'soapbuflen':'', \
            'prefix':'', \
            'config':'', \
            'policy':'', \
            'verbose':'' \
        }

    USERDATA_B = {\
        'username':'', \
            'password':'', \
            'ifolderws':'', \
            'pathtodb':'', \
            'soapbuflen':'', \
            'prefix':'', \
            'config':'', \
            'policy':'', \
            'verbose':'' \
        }

    WAIT_FOR_SIMIAS_TO_UPDATE = 5

    def __init__ (self):
        self.load_configuration ()

    def load_configuration (self):
        if os.path.isfile (self.SETUP_INI):
            config = ConfigParser.RawConfigParser ()
            config.read (self.SETUP_INI)
            
            USERDATA = ['USERDATA_A', 'USERDATA_B']

            for USER in USERDATA:
                if config.has_section (USER):
                    for key in Setup.__dict__[USER].keys ():
                        if config.has_option (USER, key):
                            Setup.__dict__[USER][key] = config.get (USER, key)
                        else:
                            print >> sys.stderr, \
                                'Error : could not find ' \
                                'configuration parameter `{0}\' in ' \
                                'section `{1}\'. Aborting.'.format (key, USER)
                            sys.exit ()
                    try:
                        Setup.__dict__[USER]['soapbuflen'] = \
                            config.getint (USER, 'soapbuflen')
                        Setup.__dict__[USER]['verbose'] = \
                            config.getboolean (USER, 'verbose')
                    except ConfigParser.Error, cpe:
                        print >> sys.stderr, cpe
                else:
                    print >> sys.stderr, \
                        'Error : could not find ' \
                        'configuration section `{0}\'. ' \
                        'Aborting.'.format (USER)
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

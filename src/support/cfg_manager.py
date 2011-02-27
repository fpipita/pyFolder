# -*- coding: utf-8 -*-

from optparse import OptionParser
from policy import PolicyFactory

import sys

class CfgManager ():
    class CfgFile:
        def __init__ (self, ifcm):
            pass

    def __init__ (self, configfile=None, \
                      pathtodb=None, \
                      soapbuflen=None, \
                      runfromtest=False):

        # Try to read the configuration file
        CfgManager.CfgFile (self)
        
        # If the user provides any command line option, just overwrite the 
        # settings previously read from the configuration file
        self.parser = OptionParser ()

        self.parser.add_option ('--username', \
                                    action='store', \
                                    type='string', \
                                    dest='username', \
                                    help='The username that you use to ' \
                                    'login into your iFolder account (MANDATORY)')

        self.parser.add_option ('--password', \
                                    action='store', \
                                    type='string', \
                                    dest='password', \
                                    help='The password that you use to ' \
                                    'login into your iFolder account (MANDATORY)')

        self.parser.add_option ('--ifolderws', \
                                    action='store', \
                                    type='string', \
                                    dest='ifolderws', \
                                    help='Use `IFOLDERWS\' as the iFolder Web ' \
                                    'Service URI (MANDATORY)')

        self.parser.add_option ('--prefix', \
                                    action='store', \
                                    type='string', \
                                    dest='prefix', \
                                    help='Use `PREFIX\' as root path where ' \
                                    'to create the local repository ' \
                                    '[ default: %default ]', \
                                    default='')

        self.parser.add_option ('--soapbuflen', \
                                    action='store', \
                                    type='int', \
                                    dest='soapbuflen', \
                                    help='Bufferize up to `SOAPBUFLEN\' ' \
                                    'bytes before to flush the buffers ' \
                                    'during the download/upload ' \
                                    '[ default : %default ]', \
                                    default=soapbuflen)

        self.parser.add_option ('--config', \
                                    action='store', \
                                    type='string', \
                                    dest='configfile', \
                                    help='Read the configuration from ' \
                                    '`CONFIGFILE\' [ default : %default ]', \
                                    default=configfile)

        self.parser.add_option ('--pathtodb', \
                                    action='store', \
                                    type='string', \
                                    dest='pathtodb', \
                                    help='The path to a local SQLite ' \
                                    'database on which pyFolder relies ' \
                                    'to detect local and remote changes ' \
                                    '[ default : %default ]', \
                                    default=pathtodb)

        self.parser.add_option ('--action', \
                                    action='store', \
                                    type='choice', \
                                    dest='action', \
                                    help='The action that will be done by ' \
                                    'pyFolder [ default: %default ]', \
                                    choices=self.__actions (), \
                                    default=self.__actions ()[0])

        self.parser.add_option ('--policy', \
                                    action='store', \
                                    type='choice', \
                                    dest='policy', \
                                    help='The way pyFolder will behave ' \
                                    'whether it detects any conflict ' \
                                    'between the local copy of the ' \
                                    'repository and the remote one ' \
                                    '[ default : %default ]', \
                                    choices=self.__policies (), \
                                    default=self.__policies ()[0])
                                
        self.parser.add_option ('--verbose', '-v', \
                                    action='store_true', \
                                    dest='verbose', \
                                    help='Starts pyFolder in verbose mode, ' \
                                    'printing debug/error messages ' \
                                    'on the stderr [ default : %default ]', \
                                    default=False)
        
        (self.options, self.args) = self.parser.parse_args ()

        if runfromtest:
            return

        if self.options.username is None or self.options.password is None \
                or self.options.ifolderws is None:
            self.parser.print_help ()
            sys.exit ()
        if self.options.action == 'checkout' and \
                self.options.policy != self.__policies ()[0]:
            self.parser.error ('You can\'t use the `--policy\' switch ' \
                                   'while running the `checkout\' action.')

    def __actions (self):
        return [\
            'checkout', \
                'update', \
                'commit' \
                ]
    
    def __policies (self):
        return PolicyFactory.get_factories ()
    
    def get_policy (self):
        return self.options.policy

    def get_action (self):
        return self.options.action

    def get_username (self):
        return self.options.username

    def get_password (self):
        return self.options.password
    
    def get_prefix (self):
        return self.options.prefix

    def get_ifolderws (self):
        return self.options.ifolderws
    
    def get_soapbuflen (self):
        return self.options.soapbuflen

    def get_pathtodb (self):
        return self.options.pathtodb

    def get_verbose (self):
        return self.options.verbose

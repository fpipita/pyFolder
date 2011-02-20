from optparse import OptionParser
import sys

class CfgManager ():
    class CfgFile:
        def __init__ (self, ifcm):
            pass

    def __init__ (self, configfile, pathtodb, soapbuflen):

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
                                    'login into your iFolder account')

        self.parser.add_option ('--password', \
                                    action='store', \
                                    type='string', \
                                    dest='password', \
                                    help='The password that you use to ' \
                                    'login into your iFolder account')

        self.parser.add_option ('--ifolderws', \
                                    action='store', \
                                    type='string', \
                                    dest='ifolderws', \
                                    help='The iFolder Web Service URI')

        self.parser.add_option ('--soapbuflen', \
                                    action='store', \
                                    type='int', \
                                    dest='soapbuflen', \
                                    help='Bufferize up to SOAPBUFLEN bytes ' \
                                    'before to flush [ default : %default ]', \
                                    default=soapbuflen)

        self.parser.add_option ('--config', \
                                    action='store', \
                                    type='string', \
                                    dest='configfile', \
                                    help='Read the configuration from ' \
                                    'CONFIGFILE [ default : %default ]', \
                                    default=configfile)

        self.parser.add_option ('--pathtodb', \
                                    action='store', \
                                    type='string', \
                                    dest='pathtodb', \
                                    help='The path to a local sqlite ' \
                                    'database containing the mapping ' \
                                    'between the entry-IDs and their ' \
                                    'modification times [ default : ' \
                                    '%default ]', \
                                    default=pathtodb)

        self.parser.add_option ('--action', \
                                    action='store', \
                                    type='choice', \
                                    dest='action', \
                                    help='The action that will be done by ' \
                                    'pyFolder [ default: %default ]', \
                                    choices=self.actions (), \
                                    default=self.actions ()[0])

        self.parser.add_option ('--verbose', '-v', \
                                    action='store_true', \
                                    dest='verbose', \
                                    help='Starts pyFolder in verbose mode, ' \
                                    'printing debug/error messages ' \
                                    'on the stderr [ default : %default ]', \
                                    default=False)
                                    
        (self.options, self.args) = self.parser.parse_args ()
        if self.options.username is None or self.options.password is None \
                or self.options.ifolderws is None:
            self.parser.print_help ()
            sys.exit ()

    def actions (self):
        return [\
            'checkout', \
             'update' \
                ]

    def action (self):
        return self.options.action

    def username (self):
        return self.options.username

    def password (self):
        return self.options.password

    def ifolderws (self):
        return self.options.ifolderws
    
    def soapbuflen (self):
        return self.options.soapbuflen

    def pathtodb (self):
        return self.options.pathtodb

    def verbose (self):
        return self.options.verbose

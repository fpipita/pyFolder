# -*- coding: utf-8 -*-



import ConfigParser
import os
import sys



SETUP_INI = 'setup.ini'
SIMIAS_REFRESH = 5



# The setup.ini file, must provide at least these two users.

PRIMARY_USER = 'PRIMARY_USER'
SECONDARY_USER = 'SECONDARY_USER'



# Error messages

SECTION_NOT_FOUND = \
    'ERROR : Could not find configuration ' \
    'section `{0}\'. Aborting.'

PARAMETER_NOT_FOUND = \
    'ERROR : Could not find ' \
    'configuration parameter `{0}\' in ' \
    'section `{1}\'. Aborting.'

INVALID_PREFIX = \
    'ERROR: The `prefix\' setting in the' \
    '`PRIMARY_USER\' section can\'t either be an ' \
    'already existing path or an empty one.' \
    'Aborting.'

INVALID_REFRESH = \
    'WARNING : The SIMIAS_REFRESH option ' \
    'does not contain a valid value, defaulting ' \
    'to {0} seconds.'

CONFIG_FILE_NOT_FOUND = \
    'ERROR : Could not read the ' \
    'configuration file `{0}\'. ' \
    'Aborting.'

MANDATORY_USERS_NOT_FOUND = \
    'ERROR : Could not find mandatory users ' \
    '`PRIMARY_USER\' and `SECONDARY_USER\' in the `{0}\' ' \
    'configuration file. Aborting.'



class Setup:



    def __init__ (self, config_file=SETUP_INI):

        self.SETUP_INI = config_file
        self.USERDATA = {}
        self.load_configuration ()



    ## Display an error message and return to the operating system.
    #
    #  @param message The message to display.
    #  @param args A tuple containing format parameters for message.

    def error (self, message, args=None):

        if args is not None:
            message = message.format (*args)

        print >> sys.stderr, message
        sys.exit ()



    def create_userdict (self):

        return {
            'username': lambda username, USERDICT : username,
            'password': lambda password, USERDICT : password,
            'ifolderws': lambda ifolderws, USERDICT : ifolderws,
            'pathtodb': lambda pathtodb, USERDICT : \
                os.path.join (USERDICT['prefix'], pathtodb),
            'soapbuflen': lambda soapbuflen, USERDICT : int (soapbuflen),
            'prefix': lambda prefix, USERDICT : prefix,
            'config': lambda config, USERDICT : \
                os.path.join (USERDICT['prefix'], config),
            'policy': lambda policy, USERDICT : policy,
            'verbose': lambda verbose, USERDICT : verbose == 'True'
            }



    def load_configuration (self):

        if os.path.isfile (self.SETUP_INI):
            config = ConfigParser.RawConfigParser ()
            config.read (self.SETUP_INI)

            USERDATA_SECTIONS = config.sections ()

            if PRIMARY_USER not in USERDATA_SECTIONS or \
                    SECONDARY_USER not in USERDATA_SECTIONS:
                self.error (MANDATORY_USERS_NOT_FOUND, (self.SETUP_INI, ))

            try:

                USERDATA_SECTIONS.remove ('Options')

            except ValueError:
                pass

            USERDICT = None
            for SECTION in USERDATA_SECTIONS:

                if config.has_section (SECTION):

                    USERDICT = self.create_userdict ()

                    keys = USERDICT.keys ()
                    keys.insert (0, keys.pop (keys.index ('prefix')))

                    for key in keys:

                        if config.has_option (SECTION, key):
                            try:

                                USERDICT[key] = USERDICT[key] (\
                                    config.get (SECTION, key), USERDICT)

                            except Exception, e:
                                self.error (e)

                        else:
                            self.error (PARAMETER_NOT_FOUND, (key, SECTION))

                else:
                    self.error (SECTION_NOT_FOUND, (SECTION,))

                self.USERDATA[SECTION] = USERDICT

            if os.path.exists (self.USERDATA[PRIMARY_USER]['prefix']) or \
                    self.USERDATA[PRIMARY_USER]['prefix'] == '':
                self.error (INVALID_PREFIX)

            if config.has_section ('Options'):

                if config.has_option ('Options', 'SIMIAS_REFRESH'):

                    try:

                        self.SIMIAS_REFRESH = \
                            config.getfloat ('Options', 'SIMIAS_REFRESH')

                    except ConfigParser.Error:

                        self.SIMIAS_REFRESH = SIMIAS_REFRESH
                        self.error (INVALID_REFRESH, (self.SIMIAS_REFRESH, ))

        else:
            self.error (CONFIG_FILE_NOT_FOUND, (self.SETUP_INI, ))

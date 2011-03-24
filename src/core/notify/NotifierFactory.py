from NullNotifier import *



try:
    from WindowsNotifier import *
except:
    pass



class NotifierFactory:



    ## Creates a new instance of a Notifier subclass.
    #
    #  @param platform A string containing the host operating
    #                  system platform name.

    @staticmethod
    def create (platform):

        if platform == 'win32':
            return WindowsNotifier ()

        return NullNotifier ()

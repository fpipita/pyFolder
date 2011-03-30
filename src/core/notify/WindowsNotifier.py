# -*- coding: utf-8 -*-



from Notifier import *
from win32.pyFolderWindow import *



## A Notifier that shows baloons in the Microsoft Windows
## system tray.

class WindowsNotifier (Notifier):



    def __init__ (self, pyFolder):
        Notifier.__init__ (self, pyFolder)
        self.window = pyFolderWindow (self.pyFolder)



    def __del__ (self):
        self.window.quit ()



    def info (self, title, text):
        self.window.info (title, text)



    def warning (self, title, text):
        self.window.warning (title, text)



    def error (self, title, text):
        self.window.error (title, text)

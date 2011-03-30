from ctypes import *
from ctypes.wintypes import *
from threading import Thread
from threading import Condition



from win32con import *



# Constants

PYFOLDER_NAME = u'pyFolder'
PYFOLDER_QUIT = 1024

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETFOCUS = 0x00000003
NIM_SETVERSION = 0x00000004

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_STATE = 0x00000008
NIF_INFO = 0x00000010
NIF_GUID = 0x00000020
NIF_REALTIME = 0x00000040
NIF_SHOWTIP = 0x00000080

NIS_HIDDEN = 0x00000001
NIS_SHAREDICON = 0x00000002

NIIF_NONE = 0x00000000
NIIF_INFO = 0x00000001
NIIF_WARNING = 0x00000002
NIIF_ERROR = 0x00000003
NIIF_USER = 0x00000004
NIIF_NOSOUND = 0x00000010
NIIF_LARGE_ICON = 0x00000020
NIIF_RESPECT_QUIET_TIME = 0x00000080
NIIF_ICON_MASK = 0x0000000F



# Custom messages

WMAPP_NOTIFYCALLBACK = WM_APP + 1



# Prototypes

WNDPROC = WINFUNCTYPE (c_long, HWND, UINT, WPARAM, LPARAM)



# Structs

class NOTIFYICONDATA (Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('hWnd', HWND),
        ('uID', UINT),
        ('uFlags', UINT),
        ('uCallbackMessage', UINT),
        ('hIcon', HICON),
        ('szTip', c_wchar * 128),
        ('dwState', DWORD),
        ('dwStateMask', DWORD),
        ('szInfo', c_wchar * 256),
        ('uTimeoutOrVersion', UINT),
        ('szInfoTitle', c_wchar * 64),
        ('dwInfoFlags', DWORD)]



class WNDCLASSEX (Structure):
    _fields_ = [
        ('cbSize', UINT),
        ('style', UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', c_int),
        ('cbWndExtra', c_int),
        ('hInstance', HINSTANCE),
        ('hIcon', HICON),
        ('hCursor', HANDLE),
        ('hbrBackground', HBRUSH),
        ('lpszMenuName', c_wchar_p),
        ('lpszClassName', c_wchar_p),
        ('hIconSm', HICON)]



# Wrappers

RegisterClassEx = windll.user32.RegisterClassExW
CreateWindowEx = windll.user32.CreateWindowExW
UpdateWindow = windll.user32.UpdateWindow
Shell_NotifyIcon = windll.shell32.Shell_NotifyIconW
DefWindowProc = windll.user32.DefWindowProcW
GetMessage = windll.user32.GetMessageW
TranslateMessage = windll.user32.TranslateMessage
DispatchMessage = windll.user32.DispatchMessageW
GetModuleHandle = windll.kernel32.GetModuleHandleW
LoadIcon = windll.user32.LoadIconW
LoadCursor = windll.user32.LoadCursorW
PostQuitMessage = windll.user32.PostQuitMessage
DestroyWindow = windll.user32.DestroyWindow
CreatePopupMenu = windll.user32.CreatePopupMenu
AppendMenu = windll.user32.AppendMenuW
SetForegroundWindow = windll.user32.SetForegroundWindow
TrackPopupMenu = windll.user32.TrackPopupMenu
GetCursorPos = windll.user32.GetCursorPos
PostMessage = windll.user32.PostMessageW
ShowWindow = windll.user32.ShowWindow
DestroyMenu = windll.user32.DestroyMenu



class pyFolderWindow (Thread):
    


    def __init__ (self, pyFolder):
        Thread.__init__ (self)

        self.pyFolder = pyFolder

        self.c = Condition ()
        self.hWnd = None
        self.start ()
        

    
    def run (self):
        self.__win_main ()
        


    def quit (self):

        self.__wait ()
        self.pyFolder.stop ()
        PostMessage (self.hWnd, WM_DESTROY, None, None)
            
    

    def info (self, title, text):
        self.__show_baloon (title, text, NIIF_INFO)
        
        

    def warning (self, title, text):
        self.__show_baloon (title, text, NIIF_WARNING)



    def error (self, title, text):
        self.__show_baloon (title, text, NIIF_ERROR)



    def __wait (self):
        self.c.acquire ()

        while self.hWnd is None:
            self.c.wait ()

        self.c.release ()



    def __show_baloon (self, szInfoTitle, szInfo, dwInfoFlags):

        self.__wait ()

        nid = NOTIFYICONDATA ()
        nid.cbSize = sizeof (nid)
        nid.uFlags = NIF_INFO
        nid.hWnd = self.hWnd
        nid.uID = 0
        nid.dwInfoFlags = dwInfoFlags
        nid.szInfoTitle = szInfoTitle
        nid.szInfo = szInfo

        Shell_NotifyIcon (NIM_MODIFY, byref (nid))



    def __show_context_menu (self, hWnd, uMsg, wParam, lParam):

        if lParam == WM_RBUTTONUP:

            hMenu = CreatePopupMenu ()
            pt = POINT ()

            GetCursorPos (byref (pt))
            AppendMenu (hMenu, MF_STRING, PYFOLDER_QUIT, u'Quit')
            SetForegroundWindow (hWnd)
            TrackPopupMenu (hMenu, TPM_LEFTALIGN, pt.x, pt.y, 0, hWnd, None)
            PostMessage (hWnd, WM_NULL, 0, 0)
            return 1



    def __on_command (self, hWnd, uMsg, wParam, lParam):
        wmID = wParam & 0xFFFF

        if wmID == PYFOLDER_QUIT:
            self.quit ()



    def __wnd_proc (self, hWnd, uMsg, wParam, lParam):

        if uMsg == WM_CREATE:
            self.__add_notification_icon (hWnd)

        elif uMsg == WM_DESTROY:
            self.__delete_notification_icon (hWnd)
            PostQuitMessage (0)

        elif uMsg == WM_COMMAND:
            self.__on_command (hWnd, uMsg, wParam, lParam)

        elif uMsg == WMAPP_NOTIFYCALLBACK:
            self.__show_context_menu (hWnd, uMsg, wParam, lParam)

        else:
            return DefWindowProc (hWnd, uMsg, wParam, lParam)

        return 0



    def __delete_notification_icon (self, hWnd):
        nid = NOTIFYICONDATA ()
        nid.cbSize = sizeof (nid)
        nid.hWnd = hWnd
        nid.uID = 0

        Shell_NotifyIcon (NIM_DELETE, byref (nid))



    def __add_notification_icon (self, hWnd):
        nid = NOTIFYICONDATA ()
        nid.cbSize = sizeof (nid)
        nid.hWnd = hWnd
        nid.uID = 0
        nid.uFlags = NIF_ICON | NIF_TIP | NIF_MESSAGE
        nid.uCallbackMessage = WMAPP_NOTIFYCALLBACK
        nid.hIcon = self.__load_icon ()
        nid.szTip = PYFOLDER_NAME

        Shell_NotifyIcon (NIM_ADD, byref (nid))
        


    def __load_icon (self):
        return LoadIcon (None, IDI_APPLICATION)



    def __win_main (self):
        wcex = WNDCLASSEX ()
        wcex.cbSize = sizeof (wcex)
        wcex.style = CS_HREDRAW | CS_VREDRAW
        wcex.lpfnWndProc = WNDPROC (self.__wnd_proc)
        wcex.cbClsExtra = 0
        wcex.cbWndExtra = 0
        wcex.hInstance = GetModuleHandle (None)
        wcex.hIcon = LoadIcon (None, IDI_APPLICATION)
        wcex.hCursor = LoadCursor (None, IDC_ARROW)
        wcex.hbrBackground = HBRUSH (COLOR_WINDOW + 1)
        wcex.lpszMenuName = None
        wcex.lpszClassName = PYFOLDER_NAME

        RegisterClassEx (byref (wcex))
        
        self.c.acquire ()
        
        self.hWnd = CreateWindowEx (\
            0, PYFOLDER_NAME, PYFOLDER_NAME, WS_OVERLAPPED | WS_SYSMENU, \
                CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, \
                None, None, wcex.hInstance, None)
        
        self.c.notify ()
        self.c.release ()

        if self.hWnd:
            UpdateWindow (self.hWnd)

            msg = MSG ()

            while (GetMessage (byref (msg), None, 0, 0)):
                TranslateMessage (byref (msg))
                DispatchMessage (byref (msg))

        return 0

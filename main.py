import webview
import os
import sys
import threading
import time
from server.api.core import Api
import logging

# PyInstaller compatible: get resource file root directory
if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# optional tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_PYSTRAY = True
except Exception:
    _HAS_PYSTRAY = False

# toggle tray-related logging
_TRAY_LOG = False

def _tlog(*args, **kwargs):
    if _TRAY_LOG:
        print(*args, **kwargs)
# event used to keep process alive until user quits from tray
_TRAY_QUIT_EVENT = threading.Event()

# Platform detection
_IS_WINDOWS = os.name == 'nt'
_IS_MACOS = sys.platform == 'darwin'
_wndproc_ref = None  # prevent GC of the callback
_original_wndproc = None

# macOS helper: bring window to front using NSApplication
if _IS_MACOS:
    def _bring_window_to_front_macos():
        """Activate the application and bring all windows to front on macOS."""
        try:
            import subprocess
            pid = int(os.getpid())
            subprocess.Popen([
                'osascript', '-e',
                f'tell application "System Events" to set frontmost of '
                f'the first process whose unix id is {pid} to true'
            ])
            return True
        except Exception as e:
            _tlog(f"[Tray] macOS bring front error: {e}")
            return False

if _IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        # Select correct 64/32-bit function
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            _SetWindowLongPtr = user32.SetWindowLongPtrW
            _GetWindowLongPtr = user32.GetWindowLongPtrW
            _SetWindowLongPtr.restype = ctypes.c_void_p
            _SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            _GetWindowLongPtr.restype = ctypes.c_void_p
            _GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
        else:
            _SetWindowLongPtr = user32.SetWindowLongW
            _GetWindowLongPtr = user32.GetWindowLongW

        _CallWindowProcW = user32.CallWindowProcW
        _CallWindowProcW.restype = ctypes.c_long
        _CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        def _bring_window_to_front_by_title(title):
            try:
                hwnd = user32.FindWindowW(None, title)
                if hwnd:
                    SW_RESTORE = 9
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.SetForegroundWindow(hwnd)
                    _tlog(f"[Tray] brought window '{title}' to front (hwnd={hwnd})")
                    return True
            except Exception as e:
                _tlog(f"[Tray] Win32 bring front error: {e}")
            return False
    except Exception:
        _IS_WINDOWS = False

    # additional helper: bring front by current process id (enumerate top-level windows)
    if _IS_WINDOWS:
        try:
            EnumWindows = user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            GetWindowText = user32.GetWindowTextW
            GetWindowTextLength = user32.GetWindowTextLengthW
            GetWindowThreadProcessId = user32.GetWindowThreadProcessId

            def _bring_window_to_front_by_pid(pid):
                found = []

                @EnumWindowsProc
                def _callback(hwnd, lParam):
                    length = GetWindowTextLength(hwnd)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buf, length + 1)
                    # get process id
                    lpdw = wintypes.DWORD()
                    GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw))
                    win_pid = lpdw.value
                    if win_pid == pid:
                        found.append((hwnd, buf.value))
                    return True

                try:
                    EnumWindows(_callback, 0)
                except Exception as e:
                    _tlog(f"[Tray] EnumWindows error: {e}")
                for hwnd, title in found:
                    try:
                        SW_RESTORE = 9
                        user32.ShowWindow(hwnd, SW_RESTORE)
                        user32.SetForegroundWindow(hwnd)
                        _tlog(f"[Tray] brought hwnd={hwnd} title='{title}' to front (by pid)")
                        return True
                    except Exception as e:
                        _tlog(f"[Tray] bring by pid error for hwnd {hwnd}: {e}")
                return False
        except Exception:
            pass


def get_html_path():
    """get HTML file's absolute path"""
    return os.path.join(_BASE_DIR, 'ui', 'index.html')

def _enable_dwm_shadow(hwnd):
    """Add system shadow to window via DWM API"""
    try:
        dwmapi = ctypes.windll.dwmapi

        # DwmSetWindowAttribute(DWMWA_NCRENDERING_POLICY=2, DWMNCRP_ENABLED=2)
        # Force enable non-client area DWM rendering, prerequisite for shadow
        policy = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(policy), ctypes.sizeof(policy))

        # DwmExtendFrameIntoClientArea extends frame into client area, triggers DWM shadow
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ('cxLeftWidth', ctypes.c_int),
                ('cxRightWidth', ctypes.c_int),
                ('cyTopHeight', ctypes.c_int),
                ('cyBottomHeight', ctypes.c_int),
            ]
        m = MARGINS(1, 1, 1, 1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))

        # Windows 11 (build 22000+): enable native rounded corners
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
        try:
            corner_pref = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
        except Exception:
            pass  # Windows 10 does not support this, ignore

    except Exception as e:
        _tlog(f"[DWMShadow] error: {e}")

def _subclass_window(hwnd):
    """Subclass window procedure to implement:
    1. WM_NCCALCSIZE -> return 0, hide title bar/border (maintain frameless appearance)
    2. WM_ERASEBKGND -> return 1, prevent white background painting (eliminate flash on restore)
    """
    global _original_wndproc, _wndproc_ref

    WM_NCCALCSIZE = 0x0083
    WM_ERASEBKGND = 0x0014
    GWLP_WNDPROC = -4

    def _custom_wndproc(h, msg, wparam, lparam):
        if msg == WM_NCCALCSIZE and wparam:
            return 0
        if msg == WM_ERASEBKGND:
            return 1
        return _CallWindowProcW(_original_wndproc, h, msg, wparam, lparam)

    _wndproc_ref = WNDPROC(_custom_wndproc)
    _original_wndproc = _SetWindowLongPtr(hwnd, GWLP_WNDPROC, ctypes.cast(_wndproc_ref, ctypes.c_void_p).value)

def _setup_window_async():
    """设置窗口样式和阴影 (Windows 专用) - 已由 on_window_loaded 取代"""
    pass  # kept for backward compatibility

def _preload_libraries_async():
    """异步预加载库，不阻塞主线程"""
    try:
        api.preload_libraries()
        print("[System] Background library loading completed")
    except Exception as e:
        print(f"[System] Background library loading error: {e}")

def on_window_loaded():
    """webview loaded 回调：DOM 已就绪，立即设置窗口并显示"""
    # 窗口样式设置（无延迟）
    if _IS_WINDOWS:
        try:
            title = getattr(window, 'title', 'visualSPT')
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                GWL_STYLE = -16
                WS_CAPTION = 0x00C00000
                WS_MINIMIZEBOX = 0x00020000
                style = _GetWindowLongPtr(hwnd, GWL_STYLE)
                new_style = style | WS_CAPTION | WS_MINIMIZEBOX
                _SetWindowLongPtr(hwnd, GWL_STYLE, new_style)
                _subclass_window(hwnd)
                SWP_FRAMECHANGED = 0x0020
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                    SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
                _enable_dwm_shadow(hwnd)
        except Exception as e:
            _tlog(f"[WindowSetup] error: {e}")

    # 立即显示窗口，不等待库加载
    try:
        window.show()
        print("[GUI] Window shown via loaded event")
    except Exception as e:
        print(f"[GUI] Window show error: {e}")

def on_start_background_loading():
    """主线程启动函数：仅启动后台库加载"""
    # 异步加载库 (不阻塞 UI)
    try:
        lib_thread = threading.Thread(target=_preload_libraries_async, daemon=True)
        lib_thread.start()
    except Exception as e:
        print(f"[System] Error starting library loading thread: {e}")


def _create_tray(window, quit_event):
    if not _HAS_PYSTRAY:
        return

    def _make_image():
        try:
            logo_path = os.path.join(_BASE_DIR, 'assets', 'logo', 'logo_transparent.png')
            img = Image.open(logo_path)
            img = img.resize((64, 64), Image.LANCZOS)
            return img
        except Exception:
            img = Image.new('RGBA', (64, 64), (52, 152, 219, 255))
            d = ImageDraw.Draw(img)
            d.rectangle((12, 12, 52, 52), fill=(255, 255, 255, 255))
            return img

    def on_show(icon, item):
        try:
            _tlog('[Tray] Show clicked')
            try:
                _tlog('[Tray] window attrs:', [a for a in dir(window) if not a.startswith('_')])
            except Exception:
                pass
            # try direct call
            if hasattr(window, 'restore'):
                try:
                    _tlog('[Tray] calling window.restore()')
                    window.restore()
                except Exception as ex:
                    _tlog(f"[Tray] window.restore() error: {ex}")
            if hasattr(window, 'show'):
                try:
                    _tlog('[Tray] calling window.show()')
                    window.show()
                except Exception as ex:
                    _tlog(f"[Tray] window.show() error: {ex}")
            if hasattr(window, 'focus') and callable(getattr(window, 'focus', None)):
                try:
                    _tlog('[Tray] calling window.focus()')
                    window.focus()
                except Exception as ex:
                    _tlog(f"[Tray] window.focus() error: {ex}")
            # try to execute a small JS to focus the window if possible
            try:
                if hasattr(window, 'evaluate_js'):
                    _tlog('[Tray] calling evaluate_js to focus')
                    window.evaluate_js('window.focus && window.focus();')
            except Exception as ex:
                _tlog(f"[Tray] evaluate_js focus error: {ex}")

            # platform fallback: try platform-specific API to bring window to front
            try:
                if _IS_WINDOWS:
                    title = getattr(window, 'title', None) or getattr(window, 'uid', None)
                    if title:
                        ok = _bring_window_to_front_by_title(title)
                        if ok:
                            return
                    try:
                        pid = os.getpid()
                        _tlog(f"[Tray] attempting bring by pid={pid}")
                        ok = _bring_window_to_front_by_pid(pid)
                        if ok:
                            return
                    except Exception as ex:
                        _tlog(f"[Tray] bring by pid failed: {ex}")
                elif _IS_MACOS:
                    try:
                        ok = _bring_window_to_front_macos()
                        if ok:
                            return
                    except Exception as ex:
                        _tlog(f"[Tray] macOS bring front failed: {ex}")
            except Exception as ex:
                _tlog(f"[Tray] platform bring front error: {ex}")

            # try windows list
            try:
                for w in getattr(webview, 'windows', []):
                    try:
                        w.show()
                    except Exception:
                        pass
                return
            except Exception:
                pass
        except Exception as ex:
            _tlog(f'[Tray] show error: {ex}')

    def on_quit(icon, item):
        _tlog('[Tray] Quit clicked')
        try:
            icon.stop()
        except Exception:
            pass
        # signal main thread to exit
        try:
            quit_event.set()
        except Exception:
            pass

        # attempt to shut down the webview cleanly
        try:
            if window is not None:
                try:
                    if hasattr(window, 'destroy'):
                        window.destroy()
                except Exception:
                    pass
                try:
                    # some pywebview versions expose destroy_window
                    webview.destroy_window(window)
                except Exception:
                    pass
        except Exception:
            pass

        # final fallback: request pywebview event loop exit
        try:
            webview.exit()
        except Exception:
            pass

    icon = pystray.Icon('visualSPT', _make_image(), 'visualSPT', menu=pystray.Menu(
        pystray.MenuItem('Show', on_show, default=True),
        pystray.MenuItem('Quit', on_quit)
    ))

    # run the icon (blocking) in background thread
    try:
        icon.run()
    except Exception:
        pass

if __name__ == '__main__':
    # Prevent multiple instances
    _mutex = None
    _lock_file = None
    if _IS_WINDOWS:
        try:
            kernel32 = ctypes.windll.kernel32
            _mutex = kernel32.CreateMutexW(None, True, 'visualSPT_SingleInstance_Mutex')
            ERROR_ALREADY_EXISTS = 183
            if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
                # Another instance is running, try to activate its window and exit
                _bring_window_to_front_by_title('visualSPT')
                sys.exit(0)
        except Exception as e:
            print(f"[InstanceCheck] error: {e}")
            pass
    elif _IS_MACOS:
        try:
            import fcntl
            import atexit
            _lock_path = os.path.join(os.path.expanduser('~'), '.visualSPT.lock')
            _lock_file = open(_lock_path, 'w')
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def _release_lock():
                try:
                    fcntl.flock(_lock_file, fcntl.LOCK_UN)
                    _lock_file.close()
                except Exception:
                    pass
            atexit.register(_release_lock)
        except IOError:
            # Another instance is running
            _bring_window_to_front_macos()
            sys.exit(0)
        except Exception as e:
            print(f"[InstanceCheck] macOS lock error: {e}")

    api = Api()

    window = webview.create_window(
        title='visualSPT',
        url=get_html_path(),
        js_api=api,
        width=800,
        height=620,
        min_size=(800, 620),
        frameless=True,
        easy_drag=False,
        transparent=True,
        hidden=True,
        resizable=False,
        zoomable=False
    )
    
    api.set_window(window)

    # 注册 loaded 事件：DOM 就绪后立即设置窗口并显示
    try:
        window.events.loaded += on_window_loaded
    except Exception as e:
        print(f"[Window] attach loaded handler error: {e}")

    # start tray thread if available
    if _HAS_PYSTRAY:
        t = threading.Thread(target=_create_tray, args=(window, _TRAY_QUIT_EVENT), daemon=False)
        t.start()

    # try to intercept closing event to hide window instead
    try:
        def _on_closing(event=None):
            # prevent webview from closing, hide instead
            try:
                if event is not None and hasattr(event, 'prevent_default'):
                    event.prevent_default()
            except Exception as e:
                print(f"[Window] prevent_default error: {e}")
            try:
                window.hide()
            except Exception as e:
                print(f"[Window] hide error: {e}")

        # attach closing handler
        try:
            window.events.closing += _on_closing
        except Exception as e:
            print(f"[Window] attach closing handler error: {e}")
            # fallback: some backends may not support 'closing'; ignore
            pass
    except Exception as e:
        print(f"[Window] error in closing handler setup: {e}")

    # webview must run on the main thread
    try:
        webview.start(func=on_start_background_loading, debug=False)
        print("[GUI] webview started")
    except Exception as e:
        print(f"[GUI] webview.start error: {e}")

    # keep process alive until user chooses 'Quit' from tray
    try:
        _TRAY_QUIT_EVENT.wait()
        print("[System] Quit event received, quitting")
    except KeyboardInterrupt:
        print("[System] KeyboardInterrupt received, quitting")
        pass
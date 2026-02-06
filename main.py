import webview
import os
import sys
import threading
import time
from server.api.core import Api
import logging

# PyInstaller 兼容：获取资源文件根目录
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

# Windows helper to bring window to front using Win32 API
_IS_WINDOWS = os.name == 'nt'
_wndproc_ref = None  # prevent GC of the callback
_original_wndproc = None

if _IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        # 选择正确的 64/32 位函数
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
    """通过 DWM API 为窗口添加系统阴影"""
    try:
        dwmapi = ctypes.windll.dwmapi

        # DwmSetWindowAttribute(DWMWA_NCRENDERING_POLICY=2, DWMNCRP_ENABLED=2)
        # 强制启用非客户区 DWM 渲染，这是阴影的前提
        policy = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(policy), ctypes.sizeof(policy))

        # DwmExtendFrameIntoClientArea 扩展框架到客户区，触发 DWM 阴影
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ('cxLeftWidth', ctypes.c_int),
                ('cxRightWidth', ctypes.c_int),
                ('cyTopHeight', ctypes.c_int),
                ('cyBottomHeight', ctypes.c_int),
            ]
        m = MARGINS(1, 1, 1, 1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))

        # Windows 11 (build 22000+)：启用系统原生圆角
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
        try:
            corner_pref = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
        except Exception:
            pass  # Windows 10 不支持，忽略

    except Exception as e:
        _tlog(f"[DWMShadow] error: {e}")

def _subclass_window(hwnd):
    """子类化窗口过程，实现：
    1. WM_NCCALCSIZE → 返回0，隐藏标题栏/边框（保持无边框外观）
    2. WM_ERASEBKGND → 返回1，阻止白色背景绘制（消除恢复时闪白）
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

def on_start_background_loading():
    if _IS_WINDOWS:
        try:
            time.sleep(0.3)  
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
    api.preload_libraries()
    time.sleep(0.5)
    if window:
        window.show()


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

            # platform fallback: on Windows try Win32 API by window title
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
    # 防止程序多开：使用 Windows 命名互斥体
    _mutex = None
    if _IS_WINDOWS:
        try:
            kernel32 = ctypes.windll.kernel32
            _mutex = kernel32.CreateMutexW(None, True, 'visualSPT_SingleInstance_Mutex')
            ERROR_ALREADY_EXISTS = 183
            if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
                # 已有实例运行，尝试将其窗口激活后退出
                _bring_window_to_front_by_title('visualSPT')
                sys.exit(0)
        except Exception:
            pass

    api = Api()

    window = webview.create_window(
        title='visualSPT',
        url=get_html_path(),
        js_api=api,
        width=800,
        height=610,
        min_size=(800, 610),
        frameless=True,
        easy_drag=False,
        transparent=True,
        hidden=True,
        resizable=False,
        zoomable=False
    )
    
    api.set_window(window)

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
            except Exception:
                pass
            try:
                window.hide()
            except Exception:
                pass

        # attach closing handler
        try:
            window.events.closing += _on_closing
        except Exception:
            # fallback: some backends may not support 'closing'; ignore
            pass
    except Exception:
        pass

    # webview must run on the main thread
    try:
        webview.start(func=on_start_background_loading, debug=False)
    except Exception as e:
        print(f"[GUI] webview.start error: {e}")

    # keep process alive until user chooses 'Quit' from tray
    try:
        _TRAY_QUIT_EVENT.wait()
    except KeyboardInterrupt:
        pass
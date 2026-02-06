import webview
import os
import threading
import time
from server.api.core import Api
import logging

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
if _IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'ui', 'index.html')

def on_start_background_loading():
    api.preload_libraries()
    time.sleep(0.5)
    if window:
        window.show()


def _create_tray(window, quit_event):
    if not _HAS_PYSTRAY:
        return

    def _make_image():
        # simple square icon
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
        pystray.MenuItem('Show', on_show),
        pystray.MenuItem('Quit', on_quit)
    ))

    # run the icon (blocking) in background thread
    try:
        icon.run()
    except Exception:
        pass

if __name__ == '__main__':
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
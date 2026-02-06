import webview
import os
import threading
import time
from server.api import Api
import logging


def get_html_path():
    """get HTML file's absolute path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'ui', 'index.html')

def on_start_background_loading():
    api.preload_libraries()
    time.sleep(0.5)
    if window:
        window.show()

if __name__ == '__main__':
    api = Api()

    window = webview.create_window(
        title='visualSPT',
        url=get_html_path(),
        js_api=api,
        width=800,
        height=610,
        min_size=(800, 610),
        hidden=True,
        resizable=False
    )
    
    api.set_window(window)

    webview.start(func=on_start_background_loading, debug=False)
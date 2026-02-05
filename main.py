import webview
import os
import threading
import time
from server.api import Api
import logging

# 关闭 pywebview 的调试日志，减少干扰
logger = logging.getLogger('pywebview')
logger.setLevel(logging.CRITICAL)

def get_html_path():
    """get HTML file's absolute path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'ui', 'index.html')

def on_start_background_loading():
    """
    这个函数会在窗口启动后运行
    """
    # 稍微等待一下，让窗口先完全渲染出来，保证用户第一眼看到界面是流畅的
    time.sleep(1) 
    # 调用 API 中的预加载方法
    api.preload_libraries()

if __name__ == '__main__':
    api = Api()

    window = webview.create_window(
        title='visualSPT',
        url=get_html_path(),
        js_api=api,
        width=800,
        height=600,
        min_size=(800, 400)
    )
    
    api.set_window(window)

    # 关键修改：使用 start 的 func 参数
    # webview 启动后，会在一个单独的线程中执行 on_start_background_loading
    # 这样既不会阻塞窗口显示，也不会阻塞窗口拖动
    webview.start(func=on_start_background_loading, debug=False)
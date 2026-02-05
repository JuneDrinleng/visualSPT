import webview
import os
import threading
import time
from server.api import Api
import logging

# logger = logging.getLogger('pywebview')
# logger.setLevel(logging.CRITICAL)

def get_html_path():
    """get HTML file's absolute path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'ui', 'index.html')

def on_start_background_loading():
    """
    这个函数会在 pywebview 启动后的独立线程中运行
    """
    # 1. 执行繁重的加载任务 (阻塞操作)
    api.preload_libraries()
    
    # 2. 【关键优化】增加冷却时间
    # 库加载完后，CPU 可能会有短暂的峰值。
    # 暂停 0.5 秒，让系统完成内存整理，确保窗口显示时主线程是空闲的，防止“未响应”。
    time.sleep(0.5)
    
    # 3. 主动显示窗口
    if window:
        window.show()

if __name__ == '__main__':
    api = Api()

    window = webview.create_window(
        title='visualSPT',
        url=get_html_path(),
        js_api=api,
        width=800,
        height=600,
        min_size=(800, 400),
        hidden=True  # 初始化为隐藏状态
    )
    
    api.set_window(window)

    webview.start(func=on_start_background_loading, debug=False)
import webview
import os
import threading
import time
from server.api import Api
import logging

# 关闭 pywebview 的调试日志，减少干扰
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
    # 1. 移除 sleep，因为窗口是隐藏的，我们需要争分夺秒地加载
    # time.sleep(1) 
    
    # 2. 执行繁重的加载任务 (阻塞操作)
    # 此时用户看不到窗口，但程序在后台疯狂加载 pandas/matplotlib
    api.preload_libraries()
    
    # 3. 【关键】加载全部完成后，主动显示窗口
    # 此时用户看到的界面，已经是“完全就绪”的状态，点击任何按钮都会秒响应
    if window:
        window.show()

if __name__ == '__main__':
    api = Api()

    # 【关键修改】在创建窗口时，增加 hidden=True 参数
    # 这样程序启动时，窗口会被创建但不可见
    window = webview.create_window(
        title='visualSPT',
        url=get_html_path(),
        js_api=api,
        width=800,
        height=600,
        min_size=(800, 400),
        hidden=True  # <--- 初始化为隐藏状态
    )
    
    api.set_window(window)

    # 启动 webview，并在启动后执行 on_start_background_loading
    webview.start(func=on_start_background_loading, debug=False)
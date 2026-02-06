import io
import base64
import os
import webview

from . import io as api_io
from . import plot as api_plot


class Api:
    def __init__(self):
        self._window = None

        self.trajectories = []
        self.current_file = ""

        self.pd = None
        self.np = None
        self.plt = None
        self.read_trackmate_csv = None
        self.read_npy_traj = None
        self.read_npz_traj = None

        self.is_loading_libs = False
        self.libs_loaded = False
        self._always_on_top = False

    def set_window(self, window):
        self._window = window

    def preload_libraries(self):
        if self.libs_loaded or self.is_loading_libs:
            return

        self.is_loading_libs = True
        print("[System] Loading the libraries...")

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import pandas as pd
            import numpy as np
            from server.tool.read_traj_file import read_trackmate_csv, read_npy_traj, read_npz_traj

            self.plt = plt
            self.pd = pd
            self.np = np
            self.read_trackmate_csv = read_trackmate_csv
            self.read_npy_traj = read_npy_traj
            self.read_npz_traj = read_npz_traj

            # quick headless check
            try:
                fig = plt.figure()
                ax = fig.add_subplot(111)
                ax.plot([0, 1], [0, 1])
                fig.canvas.draw()
                plt.close(fig)
            except Exception:
                pass

            self.libs_loaded = True
            print("[System] Libraries loaded, system is ready.")
        except Exception as e:
            print(f"[System] Preload failed: {e}")
        finally:
            self.is_loading_libs = False

    def _ensure_libs(self):
        if self.libs_loaded:
            return
        print("[System] User actions too fast, switching to foreground loading...")
        self.preload_libraries()

    def process_file_dialog(self):
        self._ensure_libs()
        file_types = ('Data Files (*.csv;*.npz;*.npy)', 'All files (*.*)')

        if not self._window:
            return {"error": "Window not initialized"}

        result = self._window.create_file_dialog(allow_multiple=False, file_types=file_types)

        if not result:
            return {"cancelled": True}
        file_path = result[0]

        try:
            traj_data, traj_number = api_io.read_trajectory_from_path(file_path, self)
            self.trajectories = traj_data
            self.current_file = os.path.basename(file_path)
            first_traj_img = ""
            if traj_number > 0:
                first_traj_img = self._plot_trajectory_by_index(0)
            return {"file_path": file_path, "total_trajs": traj_number, "image": first_traj_img}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Processing error: {str(e)}"}

    def change_trajectory(self, index, scale=1.0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
        self._ensure_libs()
        try:
            index = int(index)
            scale = float(scale)
            if 0 <= index < len(self.trajectories):
                img = self._plot_trajectory_by_index(index, scale, zero_start, x_unit, y_unit, custom_title, show_markers, show_title, show_axis_labels, show_grid)
                return {"image": img}
            else:
                return {"error": "Index out of range"}
        except Exception as e:
            return {"error": str(e)}

    def change_activation(self, index, scale=1.0, fps=20, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
        """接口：为 activate-traj 页面暴露的绘图方法（激活/动态可视化变体）。"""
        self._ensure_libs()
        try:
            index = int(index)
            scale = float(scale)
            try:
                fps = int(fps)
            except Exception:
                fps = 20
            if 0 <= index < len(self.trajectories):
                img = self._plot_activation_by_index(index, scale, fps, zero_start, x_unit, y_unit, custom_title, show_markers, show_title, show_axis_labels, show_grid)
                return {"image": img}
            else:
                return {"error": "Index out of range"}
        except Exception as e:
            return {"error": str(e)}

    def save_plot(self, options):
        self._ensure_libs()
        try:
            save_path = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=f"traj_{options.get('index', 0)}.svg",
                file_types=('SVG Image (*.svg)', 'PNG Image (*.png)', 'All files (*.*)')
            )

            if not save_path:
                return {"cancelled": True}
            save_path = save_path if isinstance(save_path, str) else save_path[0]
            index = int(options.get('index', 0))
            scale = float(options.get('scale', 1.0))
            zero_start = options.get('zero_start', False)
            x_unit = options.get('x_unit', "px")
            y_unit = options.get('y_unit', "px")
            custom_title = options.get('custom_title', "")
            show_markers = options.get('show_markers', True)
            show_title = options.get('show_title', True)
            show_axis_labels = options.get('show_axis_labels', True)
            show_grid = options.get('show_grid', True)
            traj = self.trajectories[index]
            x, y = api_plot.extract_xy(traj, self.pd, self.np)

            msg = api_plot.generate_plot(
                self.plt, self.np, x, y,
                title=f"Trajectory ID: {index}",
                scale=scale,
                zero_start=zero_start,
                x_unit=x_unit,
                y_unit=y_unit,
                save_path=save_path,
                custom_title=custom_title,
                show_markers=show_markers,
                show_title=show_title,
                show_axis_labels=show_axis_labels,
                show_grid=show_grid
            )

            return {"success": True, "path": save_path}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    # Window control helpers used by frontend custom title bar
    def hide_window(self):
        try:
            if self._window:
                self._window.hide()
                return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no window"}

    def _get_hwnd(self):
        """获取窗口的 Win32 句柄"""
        hwnd = getattr(self._window, '_hwnd', None)
        if hwnd:
            return hwnd
        # fallback: 通过标题查找
        try:
            import ctypes
            return ctypes.windll.user32.FindWindowW(None, self._window.title)
        except Exception:
            return None

    def minimize_window(self):
        try:
            if self._window:
                hwnd = self._get_hwnd()
                if hwnd:
                    import ctypes
                    SW_MINIMIZE = 6
                    ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
                else:
                    self._window.minimize()
                return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no window"}

    def maximize_window(self):
        try:
            if self._window:
                self._window.maximize()
                return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no window"}

    def restore_window(self):
        try:
            if self._window:
                hwnd = self._get_hwnd()
                if hwnd:
                    import ctypes
                    SW_RESTORE = 9
                    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                else:
                    self._window.restore()
                return {"success": True}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "no window"}

    def _plot_trajectory_by_index(self, index, scale=1.0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
        traj = self.trajectories[index]
        x, y = api_plot.extract_xy(traj, self.pd, self.np)
        return api_plot.generate_plot(self.plt, self.np, x, y, title=f"Trajectory ID: {index}", scale=scale, zero_start=zero_start, x_unit=x_unit, y_unit=y_unit, custom_title=custom_title, show_markers=show_markers, show_title=show_title, show_axis_labels=show_axis_labels, show_grid=show_grid)

    def _plot_activation_by_index(self, index, scale=1.0, fps=20, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
        traj = self.trajectories[index]
        x, y = api_plot.extract_xy(traj, self.pd, self.np)
        return api_plot.generate_activation_plot(self.plt, self.np, x, y, title=f"Activation ID: {index}", scale=scale, fps=fps, zero_start=zero_start, x_unit=x_unit, y_unit=y_unit, custom_title=custom_title, show_markers=show_markers, show_title=show_title, show_axis_labels=show_axis_labels, show_grid=show_grid)

import io
import base64
import os
import webview

from . import io as api_io
from . import plot as api_plot
from server.tool.cal_msd import eamsd_cal, tamsd_cal


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
        self._loading_progress = 0      # 0-100 loading progress
        self._loading_stage = ''        # current loading stage description
        self._always_on_top = False

        # Plot cache: (params_tuple) -> base64 image string
        self._plot_cache = {}
        self._plot_cache_max = 50
        # MSD cache keyed by scale (float) -> dict with keys: lags, eamsd, tamsd_mean, tamsd_std, tamsd_arr
        self._msd_cache = {}

    def set_window(self, window):
        self._window = window

    def window_show(self):
        """显示窗口 (在前端准备就绪后调用)"""
        try:
            if self._window:
                self._window.show()
                print("[GUI] Window showed from frontend ready signal")
            return {"ok": True}
        except Exception as e:
            print(f"[GUI] Error showing window: {e}")
            return {"error": str(e)}

    def get_loading_progress(self):
        """返回当前加载进度 (0-100) 和阶段描述"""
        return {
            'progress': self._loading_progress,
            'stage': self._loading_stage,
            'done': self.libs_loaded
        }

    def preload_libraries(self):
        if self.libs_loaded or self.is_loading_libs:
            return

        self.is_loading_libs = True
        self._loading_progress = 5
        self._loading_stage = 'Loading matplotlib...'
        print("[System] Loading the libraries...")

        try:
            # Stage 1: matplotlib (heaviest)
            import matplotlib
            self._loading_progress = 20
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            self.plt = plt
            self._loading_progress = 45
            self._loading_stage = 'Loading pandas...'
            print("[System] matplotlib loaded")

            # Stage 2: pandas
            import pandas as pd
            self.pd = pd
            self._loading_progress = 65
            self._loading_stage = 'Loading numpy...'
            print("[System] pandas loaded")

            # Stage 3: numpy
            import numpy as np
            self.np = np
            self._loading_progress = 80
            self._loading_stage = 'Loading data readers...'
            print("[System] numpy loaded")

            # Stage 4: project-specific readers
            from server.tool.read_traj_file import read_trackmate_csv, read_npy_traj, read_npz_traj
            self.read_trackmate_csv = read_trackmate_csv
            self.read_npy_traj = read_npy_traj
            self.read_npz_traj = read_npz_traj
            self._loading_progress = 100
            self._loading_stage = 'Ready'

            self.libs_loaded = True
            print("[System] Libraries loaded, system is ready.")
        except Exception as e:
            self._loading_stage = f'Error: {e}'
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
            self._plot_cache.clear()  # clear cache on new file
            self._msd_cache.clear()
            first_traj_img = ""
            if traj_number > 0:
                first_traj_img = self._plot_trajectory_by_index(0)
            return {"file_path": file_path, "total_trajs": traj_number, "image": first_traj_img}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Processing error: {str(e)}"}

    def change_trajectory(self, index, scale=1.0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True, show_colorbar=True, show_ticks=True, show_border=True):
        self._ensure_libs()
        try:
            index = int(index)
            scale = float(scale)
            if 0 <= index < len(self.trajectories):
                cache_key = (index, scale, zero_start, x_unit, y_unit, custom_title,
                             show_markers, show_title, show_axis_labels, show_grid,
                             show_colorbar, show_ticks, show_border)
                if cache_key in self._plot_cache:
                    return {"image": self._plot_cache[cache_key]}
                img = self._plot_trajectory_by_index(index, scale, zero_start, x_unit, y_unit, custom_title, show_markers, show_title, show_axis_labels, show_grid, show_colorbar, show_ticks, show_border)
                if img and len(self._plot_cache) < self._plot_cache_max:
                    self._plot_cache[cache_key] = img
                return {"image": img}
            else:
                return {"error": "Index out of range"}
        except Exception as e:
            return {"error": str(e)}

    def change_activation(self, index, scale=1.0, fps=20, trail_len=0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_timebar=True, show_title=True, show_axis_labels=True, show_grid=True):
        """API for activate-traj page (activation/dynamic visualization variant)."""
        self._ensure_libs()
        try:
            index = int(index)
            scale = float(scale)
            try:
                fps = int(fps)
            except Exception:
                fps = 20
            try:
                trail_len = int(trail_len)
            except Exception:
                trail_len = 0
            if 0 <= index < len(self.trajectories):
                img = self._plot_activation_by_index(index, scale, fps, trail_len, zero_start, x_unit, y_unit, custom_title, show_timebar, show_title, show_axis_labels, show_grid)
                return {"image": img}
            else:
                return {"error": "Index out of range"}
        except Exception as e:
            return {"error": str(e)}

    def change_msd(self, index, scale=1.0, x_unit="frame", y_unit="unit", custom_title="", show_legend=True, plot_eamsd=True, plot_tamsd=True, plot_tamsd_mean=True, show_title=True, show_axis_labels=True, dt=1.0):
        self._ensure_libs()
        try:
            if len(self.trajectories) == 0:
                return {"error": "No trajectories loaded"}
            index = int(index)
            scale = float(scale)
            if index < 0 or index >= len(self.trajectories):
                return {"error": "Index out of range"}

            # Always compute ensemble statistics (EAMSD and ensemble TAMSD mean/std).
            # The `plot_eamsd` flag will only control whether EAMSD is drawn, not whether
            # it is computed.
            lags = None
            eamsd = None
            tamsd = None
            tamsd_mean = None
            tamsd_std = None
            lags, eamsd, tamsd_mean, tamsd_std = self._compute_eamsd(scale)
            # apply dt scaling to lag axis if provided by frontend
            try:
                dt = float(dt)
            except Exception:
                dt = 1.0
            if lags is not None and len(lags) > 0 and dt != 1.0:
                try:
                    lags = self.np.asarray(lags, dtype=float) * dt
                except Exception:
                    pass
            if plot_tamsd:
                tamsd = self._compute_tamsd(index, scale)

            # If neither EAMSD (when requested to plot) nor TAMSD are available, abort
            if (plot_eamsd and (eamsd is None or len(eamsd) == 0)) and (not plot_tamsd or tamsd is None or len(tamsd) == 0):
                return {"error": "No MSD data available to plot"}

            img = api_plot.generate_msd_plot(
                self.plt, self.np,
                lags if lags is not None else self.np.arange(0),
                eamsd=eamsd,
                tamsd=tamsd,
                tamsd_mean=tamsd_mean,
                tamsd_std=tamsd_std,
                title=f"MSD ID: {index}",
                x_unit=x_unit,
                y_unit=y_unit,
                custom_title=custom_title,
                show_legend=show_legend,
                show_title=show_title,
                show_axis_labels=show_axis_labels,
                plot_eamsd=plot_eamsd,
                plot_tamsd=plot_tamsd,
                plot_tamsd_mean=plot_tamsd_mean
            )
            if not img:
                return {"error": "MSD plot failed"}
            return {"image": img}
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
            show_colorbar = options.get('show_colorbar', True)
            show_ticks = options.get('show_ticks', True)
            show_border = options.get('show_border', True)
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
                show_grid=show_grid,
                show_colorbar=show_colorbar,
                show_ticks=show_ticks,
                show_border=show_border
            )

            return {"success": True, "path": save_path}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def save_msd_plot(self, options):
        self._ensure_libs()
        try:
            save_path = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=f"msd_{options.get('index', 0)}.svg",
                file_types=('SVG Image (*.svg)', 'PNG Image (*.png)', 'All files (*.*)')
            )

            if not save_path:
                return {"cancelled": True}
            save_path = save_path if isinstance(save_path, str) else save_path[0]

            index = int(options.get('index', 0))
            scale = float(options.get('scale', 1.0))
            x_unit = options.get('x_unit', "frame")
            y_unit = options.get('y_unit', "unit")
            custom_title = options.get('custom_title', "")
            show_legend = options.get('show_legend', True)
            plot_eamsd = options.get('plot_eamsd', True)
            plot_tamsd = options.get('plot_tamsd', True)
            plot_tamsd_mean = options.get('plot_tamsd_mean', True)
            show_title = options.get('show_title', True)
            show_axis_labels = options.get('show_axis_labels', True)

            # Always compute ensemble EAMSD/TAMSD mean/std; plotting controlled by flags
            lags = None
            eamsd = None
            tamsd = None
            tamsd_mean = None
            tamsd_std = None
            lags, eamsd, tamsd_mean, tamsd_std = self._compute_eamsd(scale)
            if plot_tamsd:
                tamsd = self._compute_tamsd(index, scale)
            # apply dt scaling if provided in options
            try:
                dt = float(options.get('dt', 1.0))
            except Exception:
                dt = 1.0
            if lags is not None and len(lags) > 0 and dt != 1.0:
                try:
                    lags = self.np.asarray(lags, dtype=float) * dt
                except Exception:
                    pass

            if (plot_eamsd and (eamsd is None or len(eamsd) == 0)) and (not plot_tamsd or tamsd is None or len(tamsd) == 0):
                return {"error": "No MSD data available to save"}

            api_plot.generate_msd_plot(
                self.plt, self.np,
                lags if lags is not None else self.np.arange(0),
                eamsd=eamsd,
                tamsd=tamsd,
                tamsd_mean=tamsd_mean,
                tamsd_std=tamsd_std,
                title=f"MSD ID: {index}",
                x_unit=x_unit,
                y_unit=y_unit,
                custom_title=custom_title,
                show_legend=show_legend,
                show_title=show_title,
                show_axis_labels=show_axis_labels,
                plot_eamsd=plot_eamsd,
                plot_tamsd=plot_tamsd,
                plot_tamsd_mean=plot_tamsd_mean,
                save_path=save_path
            )
            return {"success": True, "path": save_path}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def select_folder(self):
        """Open a folder selection dialog and return the chosen path."""
        try:
            result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
            if not result:
                return {"cancelled": True}
            folder = result[0] if isinstance(result, (list, tuple)) else result
            return {"path": folder}
        except Exception as e:
            return {"error": str(e)}

    def batch_save_single_plot(self, folder, options):
        """Save a single trajectory plot to a folder (used during batch save)."""
        self._ensure_libs()
        try:
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
            show_colorbar = options.get('show_colorbar', True)
            show_ticks = options.get('show_ticks', True)
            show_border = options.get('show_border', True)

            save_path = os.path.join(folder, f"traj_{index}.png")
            traj = self.trajectories[index]
            x, y = api_plot.extract_xy(traj, self.pd, self.np)
            api_plot.generate_plot(
                self.plt, self.np, x, y,
                title=f"Trajectory ID: {index}",
                scale=scale, zero_start=zero_start,
                x_unit=x_unit, y_unit=y_unit,
                save_path=save_path, custom_title=custom_title,
                show_markers=show_markers, show_title=show_title,
                show_axis_labels=show_axis_labels, show_grid=show_grid,
                show_colorbar=show_colorbar, show_ticks=show_ticks,
                show_border=show_border
            )
            return {"success": True, "path": save_path}
        except Exception as e:
            return {"error": str(e)}

    def batch_save_single_msd(self, folder, options):
        """Save a single MSD plot to a folder (used during batch save for MSD viewer)."""
        self._ensure_libs()
        try:
            index = int(options.get('index', 0))
            scale = float(options.get('scale', 1.0))
            x_unit = options.get('x_unit', "frame")
            y_unit = options.get('y_unit', "unit")
            custom_title = options.get('custom_title', "")
            show_legend = options.get('show_legend', True)
            plot_eamsd = options.get('plot_eamsd', True)
            plot_tamsd = options.get('plot_tamsd', True)
            plot_tamsd_mean = options.get('plot_tamsd_mean', True)
            show_title = options.get('show_title', True)
            show_axis_labels = options.get('show_axis_labels', True)
            dt = float(options.get('dt', 1.0))

            save_path = os.path.join(folder, f"msd_{index}.png")

            # compute ensemble stats and per-trajectory tamsd as done in change_msd
            lags, eamsd, tamsd_mean, tamsd_std = self._compute_eamsd(scale)
            if plot_tamsd:
                tamsd = self._compute_tamsd(index, scale)
            else:
                tamsd = None

            # apply dt scaling
            if lags is not None and len(lags) > 0 and dt != 1.0:
                try:
                    lags = self.np.asarray(lags, dtype=float) * dt
                except Exception:
                    pass

            api_plot.generate_msd_plot(
                self.plt, self.np,
                lags if lags is not None else self.np.arange(0),
                eamsd=eamsd,
                tamsd=tamsd,
                tamsd_mean=tamsd_mean,
                tamsd_std=tamsd_std,
                title=f"MSD ID: {index}",
                x_unit=x_unit,
                y_unit=y_unit,
                custom_title=custom_title,
                show_legend=show_legend,
                show_title=show_title,
                show_axis_labels=show_axis_labels,
                plot_eamsd=plot_eamsd,
                plot_tamsd=plot_tamsd,
                plot_tamsd_mean=plot_tamsd_mean,
                save_path=save_path
            )
            return {"success": True, "path": save_path}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def batch_save_canvas_image(self, folder, index, data_url):
        """Save a canvas-rendered PNG to a folder with indexed filename (batch save)."""
        try:
            save_path = os.path.join(folder, f"anim_{index}.png")
            header = "data:image/png;base64,"
            if data_url.startswith(header):
                data_url = data_url[len(header):]
            img_bytes = base64.b64decode(data_url)
            with open(save_path, 'wb') as f:
                f.write(img_bytes)
            return {"success": True, "path": save_path}
        except Exception as e:
            return {"error": str(e)}

    def select_gif_save_path(self, index=0):
        """Open a save dialog for GIF files and return the chosen path."""
        try:
            save_path = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=f"anim_{index}.gif",
                file_types=('GIF Animation (*.gif)', 'All files (*.*)')
            )
            if not save_path:
                return {"cancelled": True}
            save_path = save_path if isinstance(save_path, str) else save_path[0]
            return {"path": save_path}
        except Exception as e:
            return {"error": str(e)}

    def save_canvas_gif(self, save_path, frames, fps=20):
        """Assemble base64 PNG frames into a GIF file using PIL."""
        try:
            from PIL import Image
            pil_frames = []
            for data_url in frames:
                header = "data:image/png;base64,"
                if data_url.startswith(header):
                    data_url = data_url[len(header):]
                img_bytes = base64.b64decode(data_url)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                # Convert to palette mode for GIF with white background
                bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                pil_frames.append(bg.convert("RGB"))
            if not pil_frames:
                return {"error": "No frames to save"}
            duration = int(1000 / max(1, fps))
            pil_frames[0].save(
                save_path,
                save_all=True,
                append_images=pil_frames[1:],
                duration=duration,
                loop=0,
                optimize=False
            )
            return {"success": True, "path": save_path}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def save_canvas_image(self, data_url):
        """Save a base64 PNG data URL from the frontend canvas to a file."""
        try:
            save_path = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename="animation_frame.png",
                file_types=('PNG Image (*.png)', 'All files (*.*)')
            )
            if not save_path:
                return {"cancelled": True}
            save_path = save_path if isinstance(save_path, str) else save_path[0]
            header = "data:image/png;base64,"
            if data_url.startswith(header):
                data_url = data_url[len(header):]
            img_bytes = base64.b64decode(data_url)
            with open(save_path, 'wb') as f:
                f.write(img_bytes)
            return {"success": True, "path": save_path}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def save_activation_plot(self, options):
        """Save activation/animation plot as GIF file (server-side rendering for file export)."""
        self._ensure_libs()
        try:
            save_path = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=f"anim_{options.get('index', 0)}.gif",
                file_types=('GIF Animation (*.gif)', 'All files (*.*)')
            )
            if not save_path:
                return {"cancelled": True}
            save_path = save_path if isinstance(save_path, str) else save_path[0]
            index = int(options.get('index', 0))
            scale = float(options.get('scale', 1.0))
            fps = int(options.get('fps', 20))
            trail_len = int(options.get('trail_len', 0))
            zero_start = options.get('zero_start', False)
            x_unit = options.get('x_unit', "px")
            y_unit = options.get('y_unit', "px")
            custom_title = options.get('custom_title', "")
            show_timebar = options.get('show_timebar', True)
            show_title = options.get('show_title', True)
            show_axis_labels = options.get('show_axis_labels', True)
            show_grid = options.get('show_grid', True)

            traj = self.trajectories[index]
            x, y = api_plot.extract_xy(traj, self.pd, self.np)

            api_plot.generate_activation_plot(
                self.plt, self.np, x, y,
                title=f"Activation ID: {index}",
                scale=scale, fps=fps, trail_len=trail_len,
                zero_start=zero_start, x_unit=x_unit, y_unit=y_unit,
                save_path=save_path, custom_title=custom_title,
                show_timebar=show_timebar, show_title=show_title,
                show_axis_labels=show_axis_labels, show_grid=show_grid
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
        """Get the Win32 window handle"""
        hwnd = getattr(self._window, '_hwnd', None)
        if hwnd:
            return hwnd
        # fallback: find by window title
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

    def get_asset(self, filename):
        """获取资源文件的 base64 编码数据"""
        try:
            import sys
            print(f"[Asset] Requesting asset: {filename}")
            
            # 获取资源文件根目录
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            print(f"[Asset] Base dir: {base_dir}")
            file_path = os.path.join(base_dir, 'assets', filename)
            print(f"[Asset] Full path: {file_path}")
            print(f"[Asset] File exists: {os.path.exists(file_path)}")
            
            if not os.path.exists(file_path):
                error_msg = f"File not found: {filename} at {file_path}"
                print(f"[Asset] Error: {error_msg}")
                return {"error": error_msg}
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            print(f"[Asset] File size: {len(file_data)} bytes")
            
            # 根据文件扩展名确定 MIME 类型
            ext = os.path.splitext(filename)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_types.get(ext, 'application/octet-stream')
            
            # 返回 base64 编码的数据
            b64_data = base64.b64encode(file_data).decode('utf-8')
            print(f"[Asset] Successfully encoded {filename} as base64")
            return {
                "data": f"data:{mime_type};base64,{b64_data}",
                "mime": mime_type
            }
        except Exception as e:
            error_msg = f"Exception in get_asset: {str(e)}"
            print(f"[Asset] {error_msg}")
            import traceback
            traceback.print_exc()
            return {"error": error_msg}

    def _plot_trajectory_by_index(self, index, scale=1.0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True, show_colorbar=True, show_ticks=True, show_border=True):
        traj = self.trajectories[index]
        x, y = api_plot.extract_xy(traj, self.pd, self.np)
        return api_plot.generate_plot(self.plt, self.np, x, y, title=f"Trajectory ID: {index}", scale=scale, zero_start=zero_start, x_unit=x_unit, y_unit=y_unit, custom_title=custom_title, show_markers=show_markers, show_title=show_title, show_axis_labels=show_axis_labels, show_grid=show_grid, show_colorbar=show_colorbar, show_ticks=show_ticks, show_border=show_border)

    def _extract_scaled_xy(self, traj, scale=1.0):
        x, y = api_plot.extract_xy(traj, self.pd, self.np)
        x = self.np.asarray(x, dtype=float)
        y = self.np.asarray(y, dtype=float)
        valid = self.np.isfinite(x) & self.np.isfinite(y)
        x = x[valid]
        y = y[valid]
        if scale != 1.0 and scale != 0:
            x = x * scale
            y = y * scale
        return x, y

    def _compute_eamsd(self, scale=1.0):
        scale_key = float(scale)
        # reuse cached ensemble MSD if available for the same scale
        cache = self._msd_cache.get(scale_key)
        if cache is not None:
            return cache.get('lags'), cache.get('eamsd'), cache.get('tamsd_mean'), cache.get('tamsd_std')

        trajs = []
        for i in range(len(self.trajectories)):
            x, y = self._extract_scaled_xy(self.trajectories[i], scale)
            if len(x) >= 2:
                trajs.append(self.np.stack([x, y], axis=1))
        if not trajs:
            return None, None, None, None
        min_len = min(t.shape[0] for t in trajs)
        if min_len < 2:
            return None, None, None, None
        X = self.np.stack([t[:min_len] for t in trajs], axis=0)
        try:
            res = eamsd_cal(X)
        except Exception:
            # fallback: attempt old interface
            res = eamsd_cal(X)
        # eamsd_cal may return either msd array or (eamsd, tamsd_mean, tamsd_std)
        tamsd_mean = None
        tamsd_std = None
        tamsd_arr = None
        if isinstance(res, tuple) or isinstance(res, list):
            if len(res) >= 1:
                eamsd = res[0]
            else:
                eamsd = None
            if len(res) >= 2:
                tamsd_mean = res[1]
            if len(res) >= 3:
                tamsd_std = res[2]
            # optional fourth return value: full per-trajectory TAMSD array
            if len(res) >= 4:
                tamsd_arr = res[3]
        else:
            eamsd = res

        if eamsd is None:
            return None, None, None, None
        lags = self.np.arange(len(eamsd))
        # if only one trajectory in ensemble, do not provide std (no ensemble spread)
        if len(trajs) <= 1:
            tamsd_std = None
        # cache ensemble results and optional per-trajectory TAMSD array
        self._msd_cache[scale_key] = {
            'lags': lags,
            'eamsd': eamsd,
            'tamsd_mean': tamsd_mean,
            'tamsd_std': tamsd_std,
            'tamsd_arr': tamsd_arr
        }
        return lags, eamsd, tamsd_mean, tamsd_std

    def _compute_tamsd(self, index, scale=1.0):
        traj = self.trajectories[index]
        x, y = self._extract_scaled_xy(traj, scale)
        if len(x) < 2:
            return None
        traj_xy = self.np.stack([x, y], axis=1)
        # try using cached per-trajectory TAMSD from ensemble computation to avoid recompute
        cache = self._msd_cache.get(float(scale))
        if cache is not None:
            tamsd_arr = cache.get('tamsd_arr')
            if tamsd_arr is not None:
                try:
                    row = tamsd_arr[index]
                    # ensure numpy array
                    return self.np.asarray(row)
                except Exception:
                    pass
        # fallback: compute TAMSD for single trajectory
        return tamsd_cal(traj_xy)

    def get_trajectory_data(self, index, scale=1.0, zero_start=False):
        """Return raw trajectory coordinates as JSON for client-side Canvas animation."""
        self._ensure_libs()
        try:
            index = int(index)
            scale = float(scale)
            if 0 <= index < len(self.trajectories):
                traj = self.trajectories[index]
                x, y = api_plot.extract_xy(traj, self.pd, self.np)
                x = self.np.asarray(x, dtype=float)
                y = self.np.asarray(y, dtype=float)
                # filter non-finite
                valid = self.np.isfinite(x) & self.np.isfinite(y)
                x = x[valid]
                y = y[valid]
                if zero_start and len(x) > 0:
                    x = x - x[0]
                    y = y - y[0]
                if scale != 1.0 and scale != 0:
                    x = x * scale
                    y = y * scale
                return {
                    "x": x.tolist(),
                    "y": y.tolist(),
                    "length": int(len(x)),
                    "index": index
                }
            else:
                return {"error": "Index out of range"}
        except Exception as e:
            return {"error": str(e)}

    def _plot_activation_by_index(self, index, scale=1.0, fps=20, trail_len=0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_timebar=True, show_title=True, show_axis_labels=True, show_grid=True):
        traj = self.trajectories[index]
        x, y = api_plot.extract_xy(traj, self.pd, self.np)
        return api_plot.generate_activation_plot(self.plt, self.np, x, y, title=f"Activation ID: {index}", scale=scale, fps=fps, trail_len=trail_len, zero_start=zero_start, x_unit=x_unit, y_unit=y_unit, custom_title=custom_title, show_timebar=show_timebar, show_title=show_title, show_axis_labels=show_axis_labels, show_grid=show_grid)

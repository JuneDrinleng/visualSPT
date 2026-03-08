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
        self._loading_progress = 0      
        self._loading_stage = ''        
        self._always_on_top = False

        self._plot_cache = {}
        self._plot_cache_max = 50

        self._msd_cache = {}

        self._update_status = {"status": "idle", "progress": 0, "path": None, "error": None}

    def set_window(self, window):
        self._window = window

    def window_show(self):
        """Show the window (called after frontend is ready)."""
        try:
            if self._window:
                self._window.show()
                print("[GUI] Window showed from frontend ready signal")
            return {"ok": True}
        except Exception as e:
            print(f"[GUI] Error showing window: {e}")
            return {"error": str(e)}

    def get_loading_progress(self):
        """Return current loading progress (0-100) and stage description."""
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

            import matplotlib
            self._loading_progress = 20
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            self.plt = plt
            self._loading_progress = 45
            self._loading_stage = 'Loading pandas...'
            print("[System] matplotlib loaded")

            import pandas as pd
            self.pd = pd
            self._loading_progress = 65
            self._loading_stage = 'Loading numpy...'
            print("[System] pandas loaded")

            import numpy as np
            self.np = np
            self._loading_progress = 80
            self._loading_stage = 'Loading data readers...'
            print("[System] numpy loaded")

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
            self._plot_cache.clear()  
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



            lags = None
            eamsd = None
            tamsd = None
            tamsd_mean = None
            tamsd_std = None
            lags, eamsd, tamsd_mean, tamsd_std = self._compute_eamsd(scale)

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

            lags = None
            eamsd = None
            tamsd = None
            tamsd_mean = None
            tamsd_std = None
            lags, eamsd, tamsd_mean, tamsd_std = self._compute_eamsd(scale)
            if plot_tamsd:
                tamsd = self._compute_tamsd(index, scale)

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

            lags, eamsd, tamsd_mean, tamsd_std = self._compute_eamsd(scale)
            if plot_tamsd:
                tamsd = self._compute_tamsd(index, scale)
            else:
                tamsd = None

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
        """Get base64-encoded data for an asset file."""
        try:
            import sys
            print(f"[Asset] Requesting asset: {filename}")

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



    LATEST_YML_URL = "https://github.com/JuneDrinleng/visualSPT/releases/latest/download/latest.yml"

    @staticmethod
    def _parse_version(v):
        """Convert '2.12' to a comparable tuple (2, 12)."""
        try:
            return tuple(int(x) for x in str(v).strip().split('.'))
        except Exception:
            return (0,)

    @staticmethod
    def _parse_latest_yml(text):
        """Parse latest.yml with a lightweight parser (no PyYAML dependency)."""
        import re
        version_m = re.search(r'^version:\s*["\']?([\d.]+)["\']?', text, re.MULTILINE)
        version = version_m.group(1) if version_m else None

        files = []
        blocks = re.split(r'\n\s*-\s*url:', text)
        for block in blocks[1:]:
            url_m  = re.match(r'\s*["\']?([^\s"\']+)["\']?', block)
            name_m = re.search(r'name:\s*["\']?([^\s"\']+)["\']?', block)
            plat_m = re.search(r'platform:\s*["\']?([^\s"\']+)["\']?', block)
            size_m = re.search(r'size:\s*(\d+)', block)
            if url_m:
                files.append({
                    'url':      url_m.group(1).strip(),
                    'name':     name_m.group(1).strip() if name_m else '',
                    'platform': plat_m.group(1).strip() if plat_m else '',
                    'size':     int(size_m.group(1)) if size_m else 0,
                })
        return {'version': version, 'files': files}

    def get_version(self):
        """Return the current application version."""
        try:
            from server.version import __version__ as current_version
        except ImportError:
            current_version = "unknown"
        return {"version": current_version}

    def check_update(self):
        """Check GitHub for a newer version and return update info to frontend."""
        import sys
        import urllib.request
        try:
            from server.version import __version__ as current_version
        except ImportError:
            current_version = "0.0"

        try:
            req = urllib.request.Request(
                self.LATEST_YML_URL,
                headers={"User-Agent": "visualSPT-updater/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode('utf-8')
        except Exception as e:
            return {"has_update": False, "current_version": current_version, "error": str(e)}

        try:
            info = self._parse_latest_yml(content)
            remote_ver = info.get('version') or '0.0'
            if self._parse_version(remote_ver) <= self._parse_version(current_version):
                return {"has_update": False, "current_version": current_version, "remote_version": remote_ver}

            platform_key = 'win32' if sys.platform == 'win32' else ('darwin' if sys.platform == 'darwin' else sys.platform)
            matched = next((f for f in info['files'] if f.get('platform') == platform_key), None)
            if not matched:
                matched = info['files'][0] if info['files'] else {}

            import tempfile
            filename = matched.get('name', 'update')
            dest = os.path.join(tempfile.gettempdir(), filename)
            already_downloaded = (
                os.path.exists(dest)
                and os.path.getsize(dest) > 0
                and self._update_status.get("status") == "done"
                and self._update_status.get("path") == dest
            )

            return {
                "has_update":      True,
                "current_version": current_version,
                "version":         remote_ver,
                "url":             matched.get('url', ''),
                "filename":        filename,
                "size":            matched.get('size', 0),
                "has_downloaded":  already_downloaded,
                "download_path":   dest if already_downloaded else None,
            }
        except Exception as e:
            return {"has_update": False, "current_version": current_version, "error": str(e)}

    def start_download(self, url, filename):
        """Download installer in a background thread."""
        import threading, tempfile, os, urllib.request

        dest = os.path.join(tempfile.gettempdir(), filename)
        self._update_status = {"status": "downloading", "progress": 0, "path": None, "error": None}

        def _dl():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "visualSPT-updater/1.0"})
                with urllib.request.urlopen(req) as resp, open(dest, 'wb') as f:
                    total = int(resp.headers.get('Content-Length', 0))
                    downloaded = 0
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self._update_status["progress"] = min(100, int(downloaded * 100 / total))
                self._update_status["status"] = "done"
                self._update_status["path"] = dest
                self._update_status["progress"] = 100
                print(f"[Update] Download complete: {dest}")
            except Exception as e:
                self._update_status["status"] = "error"
                self._update_status["error"] = str(e)
                print(f"[Update] Download error: {e}")

        threading.Thread(target=_dl, daemon=True).start()
        return {"ok": True}

    def get_download_progress(self):
        """Return current download progress."""
        return dict(self._update_status)

    def install_update(self, path):
        """Launch installer and exit the application."""
        import threading, sys, os

        if not path or not os.path.exists(path):
            return {"error": f"Installer not found: {path}"}

        def _do():
            import time
            time.sleep(0.4)
            try:
                if sys.platform == 'win32':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.Popen(['open', path])
            except Exception as e:
                print(f"[Update] Failed to launch installer: {e}")
                return
            os._exit(0)

        threading.Thread(target=_do, daemon=True).start()
        return {"ok": True}

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

            res = eamsd_cal(X)

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

            if len(res) >= 4:
                tamsd_arr = res[3]
        else:
            eamsd = res

        if eamsd is None:
            return None, None, None, None
        lags = self.np.arange(len(eamsd))

        if len(trajs) <= 1:
            tamsd_std = None

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

        cache = self._msd_cache.get(float(scale))
        if cache is not None:
            tamsd_arr = cache.get('tamsd_arr')
            if tamsd_arr is not None:
                try:
                    row = tamsd_arr[index]

                    return self.np.asarray(row)
                except Exception:
                    pass

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

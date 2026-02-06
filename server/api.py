import io
import base64
import os
import threading
import time
import webview 


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
        self.read_npz_traj=None

        self.is_loading_libs = False
        self.libs_loaded = False

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
            from server.tool.read_traj_file import read_trackmate_csv, read_npy_traj,read_npz_traj
            
            self.plt = plt
            self.pd = pd
            self.np = np
            self.read_trackmate_csv = read_trackmate_csv
            self.read_npy_traj = read_npy_traj
            self.read_npz_traj = read_npz_traj

            try:
                fig = plt.figure()
                ax = fig.add_subplot(111)
                ax.plot([0,1], [0,1])
                fig.canvas.draw()
                plt.close(fig)
            except:
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

        if not result: return {"cancelled": True}
        file_path = result[0]
        
        try:
            if file_path.endswith('.csv'):
                traj_data, traj_number = self.read_trackmate_csv(file_path)
                self.trajectories = traj_data
                self.current_file = os.path.basename(file_path)
                
                first_traj_img = ""
                if traj_number > 0:
                    first_traj_img = self._plot_trajectory_by_index(0)
                
                return {"file_path": file_path, "total_trajs": traj_number, "image": first_traj_img}
            elif file_path.endswith('.npy'):
                traj_data, traj_number = self.read_npy_traj(file_path)
                self.trajectories = traj_data
                self.current_file = os.path.basename(file_path)
                first_traj_img = ""
                if traj_number > 0:
                    first_traj_img = self._plot_trajectory_by_index(0)
                return {"file_path": file_path, "total_trajs": traj_number, "image": first_traj_img}
            elif file_path.endswith('.npz'):
                traj_data, traj_number = self.read_npz_traj(file_path)
                self.trajectories = traj_data
                self.current_file = os.path.basename(file_path)
                first_traj_img = ""
                if traj_number > 0:
                    first_traj_img = self._plot_trajectory_by_index(0)
                return {"file_path": file_path, "total_trajs": traj_number, "image": first_traj_img}
            else:
                 return {"error": "Currently only CSV/NPY files are supported"}
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

    def save_plot(self, options): 
        self._ensure_libs()
        try:
            save_path = self._window.create_file_dialog(
                webview.SAVE_DIALOG, 
                save_filename=f"traj_{options.get('index', 0)}.svg",
                file_types=('SVG Image (*.svg)', 'PNG Image (*.png)', 'All files (*.*)')
            )
            
            if not save_path: return {"cancelled": True}
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
            x, y = self._extract_xy(traj)
            
            msg = self._generate_plot(
                x, y, 
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

    def _plot_trajectory_by_index(self, index, scale=1.0, zero_start=False, x_unit="px", y_unit="px", custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
        traj = self.trajectories[index]
        x, y = self._extract_xy(traj)
        return self._generate_plot(x, y, title=f"Trajectory ID: {index}", scale=scale, zero_start=zero_start, x_unit=x_unit, y_unit=y_unit, custom_title=custom_title, show_markers=show_markers, show_title=show_title, show_axis_labels=show_axis_labels, show_grid=show_grid)

    def _extract_xy(self, traj):
        if isinstance(traj, self.pd.DataFrame):
            if 'POSITION_X' in traj.columns and 'POSITION_Y' in traj.columns:
                return traj['POSITION_X'].values, traj['POSITION_Y'].values
            elif 'x' in traj.columns and 'y' in traj.columns:
                return traj['x'].values, traj['y'].values
        elif isinstance(traj, self.np.ndarray):
            if traj.shape[1] >= 2: return traj[:, 0], traj[:, 1]
        elif isinstance(traj, list):
            traj = self.np.array(traj)
            return traj[:, 0], traj[:, 1]
        return [], []

    def _generate_plot(self, x, y, title='Trajectory Visualization', scale=1.0, zero_start=False, x_unit="px", y_unit="px", save_path=None, custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
        plt = self.plt
        np = self.np
        from matplotlib.collections import LineCollection
        from matplotlib.colors import LinearSegmentedColormap

        plt.close('all')

        if not np.isfinite(x).all() or not np.isfinite(y).all():
            valid_mask = np.isfinite(x) & np.isfinite(y)
            x = x[valid_mask]
            y = y[valid_mask]

        if len(x) < 2: return ""

        if zero_start:
            x = x - x[0]
            y = y - y[0]
        if scale != 1.0 and scale != 0:
            x = x * scale
            y = y * scale

        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        time_axis = np.arange(len(x)) 
        
        figsize = (10, 8) if not save_path else (12, 10)
        fig, ax = plt.subplots(figsize=figsize)
        buf = io.BytesIO()

        try:
            pastel_deeper = LinearSegmentedColormap.from_list('pastel_deeper', ['#D9ECFF', '#AEEEDC', '#FFE89A'])
            
            lc = LineCollection(segments, cmap=pastel_deeper, linewidth=2, alpha=1.0)
            lc.set_array(time_axis)
            lc.set_clim(vmin=time_axis.min(), vmax=time_axis.max())
            ax.add_collection(lc)
            
            x_min, x_max = x.min(), x.max()
            y_min, y_max = y.min(), y.max()
            x_mid = 0.5 * (x_min + x_max)
            y_mid = 0.5 * (y_min + y_max)
            span_x = x_max - x_min
            span_y = y_max - y_min
            span = max(span_x, span_y)
            if span == 0: span = 1.0 
            span *= 1.1 
            half_span = span / 2
            if np.isnan(half_span) or np.isinf(half_span): half_span = 1.0
            ax.set_xlim(x_mid - half_span, x_mid + half_span)
            ax.set_ylim(y_mid - half_span, y_mid + half_span)
            ax.set_box_aspect(1)
            
            if show_markers:
                ax.plot(x[0], y[0], marker='o', color='#D9ECFF', markeredgecolor='gray', markersize=8, label='Start')
                ax.plot(x[-1], y[-1], marker='*', color='#FFE89A', markeredgecolor='gray', markersize=12, label='End')
            
            if show_title:
                final_title = custom_title if custom_title.strip() else title
                ax.set_title(final_title)
            
            if show_axis_labels:
                ax.set_xlabel(f"X ({x_unit})")
                ax.set_ylabel(f"Y ({y_unit})")
            
            if show_grid:
                ax.grid(True, linestyle='--', alpha=0.3)
            else:
                ax.grid(False)
            
            cbar = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Time (Frame)')
            
            if show_markers:
                ax.legend(loc='upper right')

            if save_path:
                fmt = 'svg'
                if save_path.lower().endswith('.png'): fmt = 'png'
                elif save_path.lower().endswith('.pdf'): fmt = 'pdf'
                fig.savefig(save_path, format=fmt, bbox_inches='tight', dpi=300)
                return "saved"
            else:
                fig.savefig(buf, format='svg', bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                return "data:image/svg+xml;base64," + img_base64

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"绘图出错: {e}")
            return ""
        finally:
            plt.close(fig)
            buf.close()
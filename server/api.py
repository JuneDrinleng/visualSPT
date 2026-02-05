import io
import base64
import os
import threading
import time

# --- 严禁在此处导入 pandas, matplotlib, numpy 或 tool.read_traj_file ---

class Api:
    def __init__(self):
        self.window = None
        self.trajectories = []
        self.current_file = ""
        
        # 库缓存
        self.pd = None
        self.np = None
        self.plt = None
        self.read_trackmate_csv = None
        
        # 状态标记
        self.is_loading_libs = False
        self.libs_loaded = False

    def set_window(self, window):
        self.window = window

    def preload_libraries(self):
        """
        供 main.py 调用的预加载函数，将在后台线程运行
        """
        if self.libs_loaded or self.is_loading_libs:
            return

        self.is_loading_libs = True
        print("[System] 正在后台静默加载数据科学库...")
        
        try:
            # 1. 设置 Matplotlib 后端 (防止 GUI 冲突的关键)
            import matplotlib
            matplotlib.use('Agg') 
            import matplotlib.pyplot as plt
            
            # 2. 导入重型库
            import pandas as pd
            import numpy as np
            from server.tool.read_traj_file import read_trackmate_csv
            
            # 3. 赋值给实例变量
            self.plt = plt
            self.pd = pd
            self.np = np
            self.read_trackmate_csv = read_trackmate_csv
            
            self.libs_loaded = True
            print("[System] 库加载完成，系统就绪。")
        except Exception as e:
            print(f"[System] 预加载失败: {e}")
        finally:
            self.is_loading_libs = False

    def _ensure_libs(self):
        """确保库已加载（如果用户手速太快，在预加载完成前点击了按钮，这里会进行同步等待）"""
        if self.libs_loaded:
            return
        
        print("[System] 用户操作过快，转为前台加载...")
        self.preload_libraries()

    def process_file_dialog(self):
        self._ensure_libs() # 确保库可用

        file_types = ('Data Files (*.csv;*.npz;*.npy)', 'All files (*.*)')
        result = self.window.create_file_dialog(
            allow_multiple=False, 
            file_types=file_types
        )

        if not result:
            return {"cancelled": True}

        file_path = result[0]
        
        try:
            if file_path.endswith('.csv'):
                # 使用 self.read_trackmate_csv
                traj_data, traj_number = self.read_trackmate_csv(file_path)
                
                self.trajectories = traj_data
                self.current_file = os.path.basename(file_path)
                
                first_traj_img = ""
                if traj_number > 0:
                    first_traj_img = self._plot_trajectory_by_index(0)
                
                return {
                    "file_path": file_path,
                    "total_trajs": traj_number,
                    "image": first_traj_img
                }
            else:
                 return {"error": "目前仅支持 CSV 文件"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"处理出错: {str(e)}"}

    def change_trajectory(self, index):
        self._ensure_libs()
        try:
            index = int(index)
            if 0 <= index < len(self.trajectories):
                img = self._plot_trajectory_by_index(index)
                return {"image": img}
            else:
                return {"error": "索引越界"}
        except Exception as e:
            return {"error": str(e)}

    def _plot_trajectory_by_index(self, index):
        traj = self.trajectories[index]
        x, y = self._extract_xy(traj)
        return self._generate_plot(x, y, title=f"Trajectory ID: {index}")

    def _extract_xy(self, traj):
        # 使用 self.pd 和 self.np
        if isinstance(traj, self.pd.DataFrame):
            if 'POSITION_X' in traj.columns and 'POSITION_Y' in traj.columns:
                return traj['POSITION_X'].values, traj['POSITION_Y'].values
            elif 'x' in traj.columns and 'y' in traj.columns:
                return traj['x'].values, traj['y'].values
        
        elif isinstance(traj, self.np.ndarray):
            if traj.shape[1] >= 2:
                return traj[:, 0], traj[:, 1]
        
        elif isinstance(traj, list):
            traj = self.np.array(traj)
            return traj[:, 0], traj[:, 1]

        return [], []

    def _generate_plot(self, x, y, title='Trajectory Visualization'):
        plt = self.plt
        np = self.np
        from matplotlib.collections import LineCollection
        from matplotlib.colors import LinearSegmentedColormap

        # 1. 清理旧图
        plt.close('all')

        # 2. 数据有效性检查 (关键修复)
        # 检查是否包含 NaN 或 Inf
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            print(f"警告: 轨迹数据包含 NaN 或 Inf，尝试清洗数据...")
            # 获取有效索引
            valid_mask = np.isfinite(x) & np.isfinite(y)
            x = x[valid_mask]
            y = y[valid_mask]

        # 如果清洗后点太少，直接返回空
        if len(x) < 2:
            print("错误: 有效轨迹点不足 2 个，无法绘图")
            return ""

        # 3. 构造绘图数据
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        time_axis = np.arange(len(x)) 
        
        fig, ax = plt.subplots()
        buf = io.BytesIO()

        try:
            # --- 绘图逻辑 ---
            pastel_deeper = LinearSegmentedColormap.from_list('pastel_deeper', ['#D9ECFF', '#AEEEDC', '#FFE89A'])
            
            lc = LineCollection(segments, cmap=pastel_deeper, linewidth=2, alpha=1.0)
            lc.set_array(time_axis)
            lc.set_clim(vmin=time_axis.min(), vmax=time_axis.max())
            ax.add_collection(lc)
            
            # --- 坐标轴范围计算 (关键修复: 增加健壮性) ---
            x_min, x_max = x.min(), x.max()
            y_min, y_max = y.min(), y.max()
            
            x_mid = 0.5 * (x_min + x_max)
            y_mid = 0.5 * (y_min + y_max)
            
            span_x = x_max - x_min
            span_y = y_max - y_min
            span = max(span_x, span_y)
            
            # 防止 span 为 0 (即所有点都在同一个位置)
            if span == 0:
                span = 1.0 
            
            span *= 1.1 # 留白 10%
            half_span = span / 2
            
            # 再次检查计算结果是否有效
            if np.isnan(half_span) or np.isinf(half_span):
                half_span = 1.0

            ax.set_xlim(x_mid - half_span, x_mid + half_span)
            ax.set_ylim(y_mid - half_span, y_mid + half_span)
            ax.set_box_aspect(1)
            
            # # --- 装饰 ---
            # ax.plot(x[0], y[0], marker='o', color='#D9ECFF', markeredgecolor='gray', markersize=8, label='Start')
            # ax.plot(x[-1], y[-1], marker='*', color='#FFE89A', markeredgecolor='gray', markersize=12, label='End')
            
            # ax.set_title(title)
            ax.grid(True, linestyle='--', alpha=0.3)
            
            cbar = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Time (Frame)')
            # ax.legend(loc='upper right')

            # 保存
            fig.savefig(buf, format='svg', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return "data:image/svg+xml;base64," + img_base64

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"绘图依然出错: {e}")
            return ""
            
        finally:
            plt.close(fig)
            buf.close()
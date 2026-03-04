# visualSPT

visualSPT 是一个面向单粒子轨迹（Single Particle Tracking, SPT）数据的桌面可视化工具，基于 `pywebview + Python` 构建。  
项目核心目标是让用户快速完成三类工作：

1. 绘制轨迹静态图
2. 绘制轨迹 GIF 动图
3. 绘制 MSD（EAMSD / TAMSD）分析图

## 主要功能

### 1) 轨迹静态图（Trajectory Visualization）
- 支持按轨迹 ID 查看与切换
- 轨迹按时间渐变着色
- 可选起点/终点标记、网格、坐标轴、标题、颜色条
- 支持缩放、原点归一（zero start）、单位自定义
- 可导出 `SVG / PNG`（MSD 也支持导出）

### 2) 轨迹动图（Animation / GIF）
- 支持逐帧播放轨迹动态过程
- 支持设置 `FPS`、拖尾长度（trail length）
- 可显示时间条和坐标辅助信息
- 可导出为 `GIF`

### 3) MSD 可视化（MSD Analysis）
- 支持 EAMSD 与单条轨迹 TAMSD 绘制
- 支持展示 TAMSD 的均值与标准差带（mean ± std）
- 对数坐标绘图，适合扩散行为分析
- 支持单位与标题自定义，支持保存图像

## 支持数据格式

- `TrackMate CSV`（按 `TRACK_ID`、`FRAME` 读取）
- `NPY`
- `NPZ`（自动识别常见轨迹键名，如 `traj`/`track`/`trajectories`）

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 运行程序

```bash
python main.py
```

## 项目结构（核心）

```text
main.py                    # 程序入口（窗口、托盘、生命周期）
server/api/core.py         # 前后端 API 聚合（文件读取、绘图、导出）
server/api/plot.py         # 轨迹图 / GIF / MSD 绘制逻辑
server/tool/read_traj_file.py  # CSV/NPY/NPZ 读取
server/tool/cal_msd.py     # EAMSD/TAMSD 计算
ui/                        # 前端页面与交互
```

## 打包命令（Windows）

```bash
pyinstaller -F -w --name "visualSPT" --icon "logo.ico" ^
  --version-file "version_info.txt" ^
  --hidden-import=server.tool.read_traj_file ^
  --hidden-import=server.tool.plot_traj ^
  --hidden-import=server.api.io ^
  --hidden-import=server.api.plot ^
  --hidden-import=matplotlib.backends.backend_svg ^
  --hidden-import=matplotlib.backends.backend_agg ^
  --hidden-import=numpy ^
  --hidden-import=pandas ^
  --hidden-import=pystray ^
  --hidden-import=pystray._win32 ^
  --hidden-import=PIL ^
  --hidden-import=PIL.Image ^
  --add-data "ui;ui" ^
  --add-data "assets;assets" ^
  main.py
```

## 依赖快照更新

```bash
pip freeze > requirements.txt
```

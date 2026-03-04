# visualSPT

语言: [English](README.md) | **中文**

visualSPT 是一个面向单粒子轨迹（SPT）数据的桌面可视化工具，基于 `pywebview + Python` 构建。

它主要解决三类任务：

1. 绘制轨迹静态图
2. 生成轨迹 GIF 动图
3. 绘制 MSD（EAMSD / TAMSD）可视化

## 功能说明

### 1) 轨迹静态图
- 按轨迹 ID 查看与切换
- 基于时间渐变着色展示轨迹
- 可选起点/终点标记、网格、坐标轴、标题、颜色条
- 支持缩放与零点归一（zero-start）
- 支持导出 `SVG` / `PNG`

### 2) 轨迹 GIF 动图
- 逐帧播放轨迹运动过程
- 可配置 `FPS` 和拖尾长度
- 可选时间条和坐标辅助信息
- 支持导出 `GIF`

### 3) MSD 可视化
- 支持 EAMSD 与单轨迹 TAMSD 曲线
- 可选 TAMSD 均值与标准差带展示
- 对数坐标绘图，便于扩散行为分析
- 支持导出 `SVG` / `PNG`

## 支持的输入格式

- `TrackMate CSV`
- `NPY`
- `NPZ`（自动识别 `traj`、`track`、`trajectories` 等常见键名）

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动程序

```bash
python main.py
```

## 核心结构

```text
main.py                        # 程序入口（窗口、托盘、生命周期）
server/api/core.py             # 后端 API 调度
server/api/plot.py             # 轨迹/GIF/MSD 绘图逻辑
server/tool/read_traj_file.py  # CSV/NPY/NPZ 数据读取
server/tool/cal_msd.py         # EAMSD/TAMSD 计算
ui/                            # 前端页面与交互
```

## 打包（Windows）

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

## 更新 `requirements.txt`

```bash
pip freeze > requirements.txt
```

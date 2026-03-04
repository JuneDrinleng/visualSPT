# visualSPT

Language: **English** | [中文](README.zh-CN.md)

visualSPT is a desktop visualization tool for Single Particle Tracking (SPT) data, built with `pywebview + Python`.

It focuses on three core tasks:

1. Plot static trajectory figures
2. Create trajectory GIF animations
3. Visualize MSD curves (EAMSD / TAMSD)

## Features

### 1) Static Trajectory Plot
- View and switch trajectories by ID
- Time-colored trajectory rendering
- Optional start/end markers, grid, axis labels, title, and colorbar
- Scale conversion and zero-start normalization
- Export to `SVG` / `PNG`

### 2) Trajectory GIF Animation
- Frame-by-frame trajectory animation
- Configurable `FPS` and trail length
- Optional time bar and axis hints
- Export animation as `GIF`

### 3) MSD Visualization
- Plot EAMSD and per-trajectory TAMSD
- Optional TAMSD mean and std band visualization
- Log-scale plotting for diffusion analysis
- Export to `SVG` / `PNG`

## Supported Input Formats

- `TrackMate CSV`
- `NPY`
- `NPZ` (auto-detects common trajectory keys like `traj`, `track`, `trajectories`)

## Quick Start

1. Install dependencies

```bash
pip install -r requirements.txt
```

2. Run

```bash
python main.py
```

## Core Structure

```text
main.py                        # App entry (window, tray, lifecycle)
server/api/core.py             # Backend API orchestration
server/api/plot.py             # Trajectory/GIF/MSD plotting logic
server/tool/read_traj_file.py  # CSV/NPY/NPZ loaders
server/tool/cal_msd.py         # EAMSD/TAMSD calculations
ui/                            # Frontend pages and interactions
```

## Build (Windows)

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

## Refresh `requirements.txt`

```bash
pip freeze > requirements.txt
```

# visualSPT

some command remind:
pack the code

```
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

Freeze the environment's requirement

```
pip freeze > requirements.txt
```

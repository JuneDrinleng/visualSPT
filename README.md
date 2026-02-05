# Beauty-Visual

```
pyinstaller -F -w --name "visualSPT" --icon "logo.ico" --hidden-import=server.tool.read_traj_file --hidden-import=matplotlib.backends.backend_svg --hidden-import=matplotlib.backends.backend_agg --hidden-import=numpy --hidden-import=pandas --add-data "ui;ui" main.py
```

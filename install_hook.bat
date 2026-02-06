@echo off
chcp 65001 >nul
REM 安装 Git Hook - 启用自动版本号更新功能
echo.
echo ====================================
echo   安装 Git Pre-Commit Hook
echo ====================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 确保 hooks 目录存在
if not exist ".git\hooks\" (
    echo [错误] 未找到 .git\hooks 目录，请确保在 Git 仓库根目录运行此脚本
    pause
    exit /b 1
)

REM 测试版本更新脚本
echo [1/3] 测试版本更新脚本...
python update_version.py
if errorlevel 1 (
    echo [警告] 版本更新脚本测试失败，但继续安装...
)

echo.
echo [2/3] 确认 Git Hook 文件已存在...
if not exist ".git\hooks\prepare-commit-msg" (
    echo [错误] prepare-commit-msg hook 文件不存在
    pause
    exit /b 1
)

echo [3/3] Git Hook 配置完成
REM Git for Windows 会自动识别 .git/hooks/prepare-commit-msg
REM prepare-commit-msg hook 会在 commit 时读取消息并智能升级版本号

echo.
echo ====================================
echo   安装完成！
echo ====================================
echo.
echo 智能版本号升级规则:
echo   - 包含"实现XX功能" → 升级主版本 (如 2.1 -> 3.0)
echo   - 包含"新增XX功能" → 升级主版本
echo   - 包含"添加XX功能" → 升级主版本
echo   - 其他情况 → 升级次版本 (如 2.1 -> 2.2)
echo.
echo 现在每次执行 'git commit -m "消息"' 时会自动更新版本号
echo.
echo 测试命令:
echo   python update_version.py "实现了新功能"  (测试主版本升级)
echo   python update_version.py "修复bug"        (测试次版本升级)
echo   test_version_logic.bat                   (完整测试)
echo.
pause

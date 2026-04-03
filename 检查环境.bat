@echo off
chcp 65001 >nul
echo ========================================
echo 环境检查工具
echo ========================================
echo.

echo [1/4] 检查 Python 环境...
python --version 2>nul
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到 PATH
    echo    请安装 Python 3.11+
) else (
    python --version
    echo ✅ Python 环境正常
)
echo.

echo [2/4] 检查 Node.js 环境...
node --version 2>nul
if errorlevel 1 (
    echo ❌ Node.js 未安装或未添加到 PATH
    echo    请安装 Node.js 16+
) else (
    node --version
    echo ✅ Node.js 环境正常
)
echo.

echo [3/4] 检查后端依赖...
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    echo ✅ 虚拟环境已创建
    .venv\Scripts\python.exe -m pip list | findstr "fastapi" >nul
    if errorlevel 1 (
        echo ⚠️  后端依赖未安装，请运行: pip install -r requirements.txt
    ) else (
        echo ✅ 后端依赖已安装
    )
) else (
    echo ⚠️  虚拟环境未创建，建议运行: python -m venv .venv
)
echo.

echo [4/4] 检查前端依赖...
if exist frontend\node_modules (
    echo ✅ 前端依赖已安装
) else (
    echo ⚠️  前端依赖未安装，请运行: cd frontend ^&^& npm install
)
echo.

echo ========================================
echo 检查完成
echo ========================================
echo.
echo 如果所有检查都通过，可以运行 启动脚本.bat 启动服务
pause


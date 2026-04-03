@echo off
chcp 65001 >nul
echo ========================================
echo APT 威胁实体对齐工具 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)
echo Python 环境检查通过
echo.

echo [2/3] 启动后端服务...
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境，将使用系统 Python
    echo 建议先创建虚拟环境: python -m venv .venv
    echo.
)
echo 正在启动后端服务...
if exist run_server.py (
    start "后端服务" cmd /k "python run_server.py"
) else (
    start "后端服务" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
)
timeout /t 3 >nul
echo 后端服务已启动（端口 8000）
echo.

echo [3/3] 启动前端服务...
cd frontend
if not exist node_modules (
    echo 检测到未安装前端依赖，正在安装...
    call npm install
    if errorlevel 1 (
        echo 错误: 前端依赖安装失败
        pause
        exit /b 1
    )
)
echo 正在启动前端服务...
start "前端服务" cmd /k "npm run dev"
timeout /t 3 >nul
echo 前端服务已启动（端口 3000）
echo.

echo ========================================
echo 启动完成！
echo ========================================
echo 后端服务: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo 前端页面: http://localhost:3000
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:3000
echo.
echo 提示: 关闭此窗口不会停止服务
echo 要停止服务，请关闭对应的服务窗口
pause


@echo off
REM ========================================
REM Translation Dashboard - 打包腳本
REM ========================================

echo ========================================
echo 正在建立發布包...
echo ========================================
echo.

set PACKAGE_NAME=Translation_Dashboard_Release
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set OUTPUT_FILE=%PACKAGE_NAME%_%TIMESTAMP%.zip

echo [1/3] 準備檔案...

REM 建立臨時目錄
if exist temp_package rmdir /s /q temp_package
mkdir temp_package\translation_dashboard

REM 複製必要檔案
echo 複製專案檔案...
xcopy /E /I /Y backend temp_package\translation_dashboard\backend
xcopy /E /I /Y frontend\src temp_package\translation_dashboard\frontend\src
xcopy /E /I /Y frontend\public temp_package\translation_dashboard\frontend\public

REM 複製前端配置檔案
copy /Y frontend\package.json temp_package\translation_dashboard\frontend\
copy /Y frontend\package-lock.json temp_package\translation_dashboard\frontend\
copy /Y frontend\index.html temp_package\translation_dashboard\frontend\
copy /Y frontend\tsconfig.json temp_package\translation_dashboard\frontend\
copy /Y frontend\tsconfig.node.json temp_package\translation_dashboard\frontend\
copy /Y frontend\vite.config.ts temp_package\translation_dashboard\frontend\

REM 複製啟動腳本
copy /Y install.bat temp_package\translation_dashboard\
copy /Y install.sh temp_package\translation_dashboard\
copy /Y start.bat temp_package\translation_dashboard\
copy /Y start.sh temp_package\translation_dashboard\

REM 複製說明文件
copy /Y README.md temp_package\translation_dashboard\
copy /Y 使用說明.txt temp_package\translation_dashboard\

REM 建立 .gitignore
echo node_modules/ > temp_package\translation_dashboard\.gitignore
echo __pycache__/ >> temp_package\translation_dashboard\.gitignore
echo *.pyc >> temp_package\translation_dashboard\.gitignore
echo .vscode/ >> temp_package\translation_dashboard\.gitignore
echo dist/ >> temp_package\translation_dashboard\.gitignore

echo.
echo [2/3] 壓縮檔案...

REM 使用 PowerShell 壓縮
powershell -command "Compress-Archive -Path 'temp_package\translation_dashboard' -DestinationPath '%OUTPUT_FILE%' -Force"

echo.
echo [3/3] 清理臨時檔案...
rmdir /s /q temp_package

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 輸出檔案: %OUTPUT_FILE%
echo.
echo 使用者可以：
echo 1. 解壓縮此檔案
echo 2. 執行 install.bat (Windows) 或 install.sh (Mac/Linux)
echo 3. 執行 start.bat (Windows) 或 start.sh (Mac/Linux)
echo.
pause

@echo off
REM ========================================
REM Translation Dashboard - 簡易打包腳本
REM ========================================

echo ========================================
echo 正在建立發布包...
echo ========================================
echo.

set OUTPUT_FILE=Translation_Dashboard_Release.zip

echo 正在壓縮專案檔案...
echo.

REM 移動到上層目錄進行壓縮
cd ..

REM 使用 PowerShell 壓縮（排除不必要的檔案）
powershell -command "$exclude = @('node_modules', '__pycache__', '.git', 'dist', '.vscode'); Get-ChildItem -Path 'translation_dashboard' -Recurse | Where-Object { $skip = $false; foreach($ex in $exclude) { if($_.FullName -like \"*\$ex*\") { $skip = $true; break } }; -not $skip } | Compress-Archive -DestinationPath 'translation_dashboard\%OUTPUT_FILE%' -Force"

cd translation_dashboard

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 輸出檔案: %OUTPUT_FILE%
echo 檔案位置: %CD%\%OUTPUT_FILE%
echo.
echo 📦 發布包已建立！
echo.
echo 使用者使用步驟：
echo 1. 解壓縮 %OUTPUT_FILE%
echo 2. Windows: 雙擊 install.bat 安裝依賴
echo 3. Windows: 雙擊 start.bat 啟動應用
echo.
echo 4. Mac/Linux: 執行 chmod +x *.sh
echo 5. Mac/Linux: 執行 ./install.sh 安裝依賴
echo 6. Mac/Linux: 執行 ./start.sh 啟動應用
echo.
pause

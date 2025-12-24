# ========================================
# Translation Dashboard - 打包腳本 (PowerShell)
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "正在建立發布包..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$OutputFile = "Translation_Dashboard_Release.zip"
$SourceDir = "."

# 要排除的目錄和檔案
$ExcludePatterns = @(
    "node_modules",
    "__pycache__",
    ".git",
    "dist",
    ".vscode",
    "*.pyc",
    ".DS_Store",
    "*.zip"
)

Write-Host "[1/3] 收集檔案..." -ForegroundColor Yellow

# 取得所有檔案，排除不需要的
$files = Get-ChildItem -Path $SourceDir -Recurse -File | Where-Object {
    $file = $_
    $shouldExclude = $false
    
    foreach ($pattern in $ExcludePatterns) {
        if ($file.FullName -like "*$pattern*") {
            $shouldExclude = $true
            break
        }
    }
    
    -not $shouldExclude
}

Write-Host "找到 $($files.Count) 個檔案" -ForegroundColor Green
Write-Host ""

Write-Host "[2/3] 建立壓縮檔..." -ForegroundColor Yellow

# 刪除舊的壓縮檔
if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

# 建立臨時目錄
$TempDir = "temp_package_$(Get-Date -Format 'yyyyMMddHHmmss')"
$TargetDir = Join-Path $TempDir "translation_dashboard"

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

# 複製檔案
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring((Get-Location).Path.Length + 1)
    $targetPath = Join-Path $TargetDir $relativePath
    $targetDir = Split-Path $targetPath -Parent
    
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    
    Copy-Item $file.FullName -Destination $targetPath -Force
}

# 壓縮
Compress-Archive -Path (Join-Path $TempDir "*") -DestinationPath $OutputFile -Force

Write-Host "壓縮完成！" -ForegroundColor Green
Write-Host ""

Write-Host "[3/3] 清理臨時檔案..." -ForegroundColor Yellow
Remove-Item -Path $TempDir -Recurse -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "打包完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 輸出檔案: $OutputFile" -ForegroundColor White
Write-Host "📁 檔案位置: $(Join-Path (Get-Location) $OutputFile)" -ForegroundColor White
Write-Host ""
Write-Host "使用者使用步驟：" -ForegroundColor Yellow
Write-Host "1. 解壓縮 $OutputFile" -ForegroundColor White
Write-Host "2. Windows: 雙擊 install.bat 安裝依賴" -ForegroundColor White
Write-Host "3. Windows: 雙擊 start.bat 啟動應用" -ForegroundColor White
Write-Host ""
Write-Host "4. Mac/Linux: 執行 chmod +x *.sh" -ForegroundColor White
Write-Host "5. Mac/Linux: 執行 ./install.sh 安裝依賴" -ForegroundColor White
Write-Host "6. Mac/Linux: 執行 ./start.sh 啟動應用" -ForegroundColor White
Write-Host ""
Write-Host "按任意鍵繼續..." -ForegroundColor Gray
Read-Host "按 Enter 繼續"

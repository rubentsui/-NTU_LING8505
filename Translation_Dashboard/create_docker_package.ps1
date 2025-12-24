# ========================================
# Translation Dashboard - Docker Package Script
# ========================================

$OutputFile = "Translation_Dashboard_Docker.zip"
$SourceDir = $PSScriptRoot

# Exclude list for Docker release
$ExcludePatterns = @(
    "node_modules",
    "__pycache__",
    ".git",
    ".gitignore",
    "dist",
    ".vscode",
    "*.pyc",
    ".DS_Store",
    "*.zip",
    "venv",
    ".env",
    "install.bat",
    "start.bat",
    "run.py",
    "Translation_Dashboard_Docker",
    "Translation_Dashboard_Release"
)

Write-Host "Creating Docker distribution package..." -ForegroundColor Cyan

# Remove old zip if exists
if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

# Create temp directory structure
$TempDir = Join-Path $env:TEMP "docker_package_$(Get-Date -Format 'yyyyMMddHHmmss')"
$TargetDir = Join-Path $TempDir "translation_dashboard"
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

# Get files
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

# Copy files preserving structure
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($SourceDir.Length + 1)
    $targetPath = Join-Path $TargetDir $relativePath
    $parentDir = Split-Path $targetPath -Parent
    
    if (-not (Test-Path $parentDir)) {
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    }
    
    Copy-Item $file.FullName -Destination $targetPath -Force
}

# Zip it
Compress-Archive -Path "$TargetDir" -DestinationPath "$SourceDir\$OutputFile" -Force

# Cleanup
Remove-Item -Path $TempDir -Recurse -Force

Write-Host "Package created: $OutputFile" -ForegroundColor Green
Write-Host "Instructions:" -ForegroundColor Yellow
Write-Host "1. Unzip the file"
Write-Host "2. Run start_docker.bat"

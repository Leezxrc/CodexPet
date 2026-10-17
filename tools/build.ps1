$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install requirements.txt first.' }
Push-Location $taskRoot
$taskOldPath = $env:PATH
$taskOldPythonPath = $env:PYTHONPATH
$taskOldPythonHome = $env:PYTHONHOME
$taskOldCache = $env:PYINSTALLER_CONFIG_DIR
try {
    # Avoid collecting unrelated developer/Qt DLLs from the caller's PATH.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $taskRoot 'build\cache'
    & $taskPython -c "from PySide6.QtGui import QImage; from PySide6.QtCore import Qt; im=QImage('assets/pet-v2.png'); im=im.scaled(256,256,Qt.KeepAspectRatio,Qt.SmoothTransformation); assert im.save('assets/pet.ico')"
    if ($LASTEXITCODE -ne 0) { throw 'Icon preparation failed.' }
    & $taskPython -m PyInstaller --noconfirm --clean --windowed --name CodexPet --distpath app --workpath build\pyinstaller --specpath build --paths "$taskRoot\src" --add-data "$taskRoot\assets\pet-v2.png;assets" --add-data "$taskRoot\assets\pet-chibi.png;assets" --icon "$taskRoot\assets\pet.ico" "$taskRoot\src\main.py"
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
} finally {
    $env:PATH = $taskOldPath
    $env:PYTHONPATH = $taskOldPythonPath
    $env:PYTHONHOME = $taskOldPythonHome
    $env:PYINSTALLER_CONFIG_DIR = $taskOldCache
    Pop-Location
}

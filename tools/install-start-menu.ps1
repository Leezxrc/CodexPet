$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskExecutable = Join-Path $taskRoot 'app\CodexPet\CodexPet.exe'
if (-not (Test-Path -LiteralPath $taskExecutable)) { throw 'CodexPet.exe was not found. Build or extract the complete app first.' }
$taskPrograms = [Environment]::GetFolderPath('Programs')
if (-not $taskPrograms) { throw 'The current user Start Menu folder could not be resolved.' }
$taskShortcutPath = Join-Path $taskPrograms 'CodexPet · 码伴.lnk'
$taskShell = New-Object -ComObject WScript.Shell
$taskShortcut = $taskShell.CreateShortcut($taskShortcutPath)
$taskShortcut.TargetPath = $taskExecutable
$taskShortcut.WorkingDirectory = $taskRoot
$taskShortcut.IconLocation = "$taskExecutable,0"
$taskShortcut.Description = 'CodexPet · 码伴 - Codex 用量桌宠'
$taskShortcut.Save()
Write-Output "Start Menu shortcut: $taskShortcutPath"

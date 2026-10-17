# CodexPet

A Windows desktop companion that displays Codex usage limits, reset cards and extra credits. Includes two appearances, head pats, dragging, a system tray menu and one-click connection.

1. Download and fully extract the [Windows release](https://github.com/Leezxrc/CodexPet/releases/latest), or clone the complete repository.
2. Open `app/CodexPet/CodexPet.exe`. Keep the adjacent `_internal` folder. Python is not required.
3. Right-click the pet → **语言 / Language / Dil** → **English**. Your choice is saved and takes effect immediately.
4. Select **Connect to Codex…** → **Connect**. An existing CLI sign-in is reused; if necessary, the official CLI is downloaded and the browser opens for sign-in. Use the same ChatGPT account as your Codex desktop app.

Click the pet’s head for a local reaction. The chibi compresses downwards and widens with its feet anchored. Drag to move; click the usage card for reset times. Right-click to change appearance, size or animation. Usage refreshes every two minutes. Missing data stays unavailable; previous data is marked as old after a failed refresh. Extra credits are credits, not money or message counts. Redeem reset cards inside Codex; this app only displays their count.

To add a Start menu shortcut, run `powershell -ExecutionPolicy Bypass -File tools\install-start-menu.ps1` from the project folder. The shortcut is named **CodexPet · 码伴**. Run the script again after moving the folder. Settings and downloaded CLI files stay under the local `data/` folder (or `%LOCALAPPDATA%/CodexPet` if the project is read-only); they are not published to GitHub.

You can also start a closed app with `CodexPet.exe --language en`. If the pet is already running, use its language menu. Head pats and animations do not call a model.

![English interface with demo data](preview-en.png)

![Connection setup](preview-connection-en.png)

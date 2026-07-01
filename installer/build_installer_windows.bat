# Windows Installer Script for CIS Agent
# This script uses PyInstaller to bundle the agent and Inno Setup to create an installer.
# For Linux, use fpm or dpkg-deb. For Mac, use pkgbuild.

# 1. Build executable with PyInstaller (package the unified service)
pyinstaller --onefile cis/service.py --name CISAgent

# 2. Create Inno Setup script (CISAgent.iss)
# [Setup]
# AppName=CIS Agent
# AppVersion=1.0
# DefaultDirName={pf64}\CISAgent
# DefaultGroupName=CISAgent
# OutputBaseFilename=CISAgentSetup
# [Files]
# Source: "dist\CISAgent.exe"; DestDir: "{app}"; Flags: ignoreversion
# [Icons]
# Name: "{group}\CIS Agent"; Filename: "{app}\CISAgent.exe"

# 3. Compile installer (requires Inno Setup)
# iscc CISAgent.iss

# 4. For auto-update, deploy a simple update server and add update check logic to the agent.
# (e.g., agent checks a version file on your server and downloads new installer if needed)

# See README for Linux/Mac packaging instructions.

; =====================================================================
; HyperSolve Desktop - per-user Windows installer
; Professional Inno Setup Script
; =====================================================================

#define MyAppName "HyperSolve"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "Bipin Vishwakarma"
#define MyAppURL "https://github.com/bipin-vishwakarma/HyperSolve"
#define MyAppExeName "HyperSolve.exe"

[Setup]
; App Identity
AppId={{D829A109-7D03-4B9F-84A8-5CF6C9B3901E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases

; User-space installation: Installs to %LocalAppData%\HyperSolve without requiring Admin UAC
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist_installer
OutputBaseFilename=HyperSolve-Setup-v{#MyAppVersion}
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern

; Silent OTA Update Configuration
CloseApplications=yes
CloseApplicationsFilter=HyperSolve.exe
RestartApplications=no
SetupIconFile=..\hypersolve\assets\hypersolve.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
WizardSizePercent=115
DisableWelcomePage=no
UsePreviousTasks=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Automatically start HyperSolve on Windows login"; GroupDescription: "Preferences:"; Flags: unchecked

[Files]
Source: "..\dist\HyperSolve\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Do not use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--tray"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel1=Welcome to HyperSolve Setup
WelcomeLabel2=Install the HyperSolve desktop app for your Windows account.%n%nPython is included. Google Chrome is required for browser sessions.%n%nYour existing browser data will be preserved.

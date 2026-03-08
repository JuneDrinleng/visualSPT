; visualSPT NSIS Installer Script
; Build: makensis /DAPPVERSION=2.12 installer.nsi
; Silent install: visualSPT-Setup.exe /S

Unicode True

!define APPNAME "visualSPT"
!define PUBLISHER "JuneDrinleng"

; Allow version to be passed on command line: /DAPPVERSION=x.y
!ifndef APPVERSION
  !define APPVERSION "1.0"
!endif

!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"

; ---- Installer icon (same as the app) ----
Icon "logo.ico"
UninstallIcon "logo.ico"

; ---- Basic settings ----
Name "${APPNAME} v${APPVERSION}"
OutFile "dist\visualSPT-Setup.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; ---- Installer pages ----
!include "MUI2.nsh"

!define MUI_ICON   "logo.ico"
!define MUI_UNICON "logo.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to ${APPNAME} v${APPVERSION} Setup"
!define MUI_WELCOMEPAGE_TEXT  "This wizard will guide you through the installation of ${APPNAME}.$\r$\n$\r$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME

; Directory selection page
!insertmacro MUI_PAGE_DIRECTORY

; Install progress page
!insertmacro MUI_PAGE_INSTFILES

; Finish page — offer to launch the app
!define MUI_FINISHPAGE_RUN        "$INSTDIR\visualSPT.exe"
!define MUI_FINISHPAGE_RUN_TEXT   "Launch ${APPNAME} now"
!insertmacro MUI_PAGE_FINISH

; Uninstall pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ---- Install section ----
Section "Install" SEC_MAIN

  ; Kill any running instance (ignore return code)
  ExecWait 'taskkill /F /IM visualSPT.exe /T' $0

  SetOutPath "$INSTDIR"
  File "dist\visualSPT.exe"

  ; Desktop shortcut
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\visualSPT.exe" \
    "" "$INSTDIR\visualSPT.exe" 0

  ; Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" \
    "$INSTDIR\visualSPT.exe" "" "$INSTDIR\visualSPT.exe" 0
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" \
    "$INSTDIR\Uninstall.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Register in Add/Remove Programs
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"     "${APPNAME}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"  "${APPVERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"       "${PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayIcon"     "$INSTDIR\visualSPT.exe"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"  1

SectionEnd

; ---- Uninstall section ----
Section "Uninstall"

  ; Kill any running instance
  ExecWait 'taskkill /F /IM visualSPT.exe /T' $0

  ; Remove files
  Delete "$INSTDIR\visualSPT.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  ; Remove shortcuts
  Delete "$DESKTOP\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk"
  RMDir  "$SMPROGRAMS\${APPNAME}"

  ; Remove registry entries
  DeleteRegKey HKLM "${UNINSTALL_KEY}"

SectionEnd

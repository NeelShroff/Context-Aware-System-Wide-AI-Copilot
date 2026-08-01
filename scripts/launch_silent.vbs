' ==============================================================================
' System-Wide AI Copilot - 100% Silent Background Launcher
' Runs Python 3D Pet & AutoHotkey with ZERO terminal windows popping up!
' ==============================================================================
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
strPath = fso.GetParentFolderName(strScriptPath)
WshShell.CurrentDirectory = strPath

pythonExe = strPath & "\vevn\Scripts\pythonw.exe"
ahkExe = strPath & "\bin\AutoHotkey64.exe"
ahkScript = strPath & "\copilot.ahk"

' 1. Launch 3D AI Companion Overlay via pythonw.exe (0 = hidden console window)
If fso.FileExists(pythonExe) Then
    WshShell.Run """" & pythonExe & """ -m src.pet.vrm_pet_gui", 0, False
Else
    pythonExe = strPath & "\vevn\Scripts\python.exe"
    WshShell.Run """" & pythonExe & """ -m src.pet.vrm_pet_gui", 0, False
End If

' 2. Launch AutoHotkey Copilot hotkey engine (0 = hidden console window)
If fso.FileExists(ahkExe) Then
    WshShell.Run """" & ahkExe & """ """ & ahkScript & """", 0, False
End If

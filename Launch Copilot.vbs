Set WshShell = CreateObject("WScript.Shell")
strPath = WScript.ScriptFullName
strFolder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(strPath)
WshShell.Run """" & strFolder & "\run_copilot.cmd""", 0, False

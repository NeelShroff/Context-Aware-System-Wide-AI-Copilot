#Requires AutoHotkey v2.0
#SingleInstance Force

; ==============================================================================
; Context-Aware System-Wide AI Writing Copilot (Windows)
; Hotkey: Ctrl + Alt + E
; AutoHotkey v2 Script
; ==============================================================================

global isProcessing := false
global statusGui := ""
global statusText := ""

; Hotkey Registration: Ctrl + Alt + E
^!e:: {
    global isProcessing
    if (isProcessing) {
        ShowStatusToast("⏳ Request already in progress...", 1500)
        return
    }

    isProcessing := true

    ; Step 1: Show initial status
    ShowStatusToast("✨ Understanding context...", 0)

    ; Step 2: Backup clipboard and capture current text selection
    savedClipboard := ClipboardAll()
    A_Clipboard := ""
    
    ; Send Ctrl+C to copy current text selection
    SendInput("^c")
    if (!ClipWait(0.8)) {
        ; No text selected
        ShowStatusToast("⚠️ No text selected", 1500)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    selectedText := A_Clipboard
    if (StrLen(Trim(selectedText)) == 0) {
        ShowStatusToast("⚠️ Selection is empty", 1500)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    ; Step 3: Collect Window Context
    try {
        activeHwnd := WinExist("A")
        activeTitle := WinGetTitle("A")
        activeProcess := WinGetProcessName("A")
        activePath := WinGetProcessPath("A")
        activeClass := WinGetClass("A")
    } catch {
        activeTitle := "Unknown"
        activeProcess := "Unknown"
        activePath := "Unknown"
        activeClass := "Unknown"
    }

    ; Step 4: Write Payload to Temporary JSON File
    reqPath := A_Temp "\ai_copilot_req.json"
    resPath := A_Temp "\ai_copilot_res.json"

    if (FileExist(reqPath))
        FileDelete(reqPath)
    if (FileExist(resPath))
        FileDelete(resPath)

    payload := Map(
        "text", selectedText,
        "context", Map(
            "title", activeTitle,
            "process", activeProcess,
            "path", activePath,
            "class", activeClass
        )
    )

    jsonStr := JSON_Serialize(payload)
    FileAppend(jsonStr, reqPath, "UTF-8-RAW")
    LogMsg("Request written to " reqPath " (len: " StrLen(selectedText) ", title: '" activeTitle "', process: '" activeProcess "')")

    ; Step 5: Update Status UI to Improving
    UpdateStatusToast("✨ Improving...")

    ; Step 6: Invoke Python Engine via helper batch file
    runnerBat := A_ScriptDir "\src\run_python.bat"
    cmdLine := Format('"{1}" "{2}" "{3}"', runnerBat, reqPath, resPath)
    LogMsg("Executing runner: " cmdLine)
    
    exitCode := RunWait(cmdLine, A_ScriptDir, "Hide")
    LogMsg("Runner finished with exitCode: " exitCode)

    ; Step 7: Process Result
    if (!FileExist(resPath)) {
        LogMsg("ERROR: Response file " resPath " was not created!")
        ShowStatusToast("❌ Error: Python execution failed", 3000)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    resStr := FileRead(resPath, "UTF-8")
    LogMsg("Response file raw content: " SubStr(resStr, 1, 200))
    resultMap := JSON_Deserialize(resStr)

    if (resultMap == "" || !resultMap.Has("success")) {
        errMsg := (StrLen(Trim(resStr)) > 0) ? SubStr(Trim(resStr), 1, 100) : "Error parsing response"
        LogMsg("ERROR: Invalid JSON response: " errMsg)
        ShowStatusToast("❌ " errMsg, 3500)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    if (!resultMap["success"]) {
        errMsg := resultMap.Has("error") ? resultMap["error"] : "Unknown error"
        LogMsg("ERROR: LLM returned failure: " errMsg)
        ShowStatusToast("❌ " errMsg, 3500)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    rewrittenText := resultMap["rewritten_text"]
    changed := resultMap.Has("changed") ? resultMap["changed"] : false
    scenarioDesc := resultMap.Has("scenario_description") ? resultMap["scenario_description"] : ""
    LogMsg("Success! Scenario: " scenarioDesc ", changed: " (changed ? "true" : "false") ", output len: " StrLen(rewrittenText))

    if (changed && StrLen(rewrittenText) > 0) {
        ; Step 8: Replace text selection in target application cleanly
        ; Ensure Ctrl and Alt modifier keys are physically released
        KeyWait("Control")
        KeyWait("Alt")
        KeyWait("e")
        Sleep(50)

        A_Clipboard := rewrittenText
        ClipWait(0.5)
        
        SendInput("^v")
        Sleep(400) ; Allow target application sufficient time to process paste buffer
        
        UpdateStatusToast("✅ Done (" scenarioDesc ")")
        SetTimer(HideStatusToast, -2000)
    } else {
        UpdateStatusToast("✅ Text optimal (no changes needed)")
        SetTimer(HideStatusToast, -2000)
    }

    ; Step 9: Restore Original Clipboard
    Sleep(100)
    A_Clipboard := savedClipboard
    isProcessing := false
}

; ==============================================================================
; Helper Functions: UI Toast Overlay
; ==============================================================================

ShowStatusToast(msg, durationMs := 0) {
    global statusGui, statusText
    
    if (statusGui != "") {
        try statusGui.Destroy()
    }

    statusGui := Gui("+AlwaysOnTop -Caption +ToolWindow +Owner")
    statusGui.BackColor := "0x1E1E2E" ; Sleek dark background
    statusGui.MarginX := 16
    statusGui.MarginY := 10
    
    statusGui.SetFont("s10 cFFFFFF q5", "Segoe UI")
    statusText := statusGui.Add("Text", "Center", msg)

    ; Calculate positioning: Bottom Right of primary screen
    MonitorGetWorkArea(1, &left, &top, &right, &bottom)
    guiX := right - 320
    guiY := bottom - 80

    statusGui.Show("X" guiX " Y" guiY " NoActivate")

    if (durationMs > 0) {
        SetTimer(HideStatusToast, -durationMs)
    }
}

UpdateStatusToast(msg) {
    global statusGui, statusText
    if (statusGui != "" && statusText != "") {
        try statusText.Value := msg
    } else {
        ShowStatusToast(msg)
    }
}

HideStatusToast() {
    global statusGui, statusText, isProcessing
    if (statusGui != "") {
        try statusGui.Destroy()
        statusGui := ""
        statusText := ""
    }
    isProcessing := false
}

; ==============================================================================
; Helper Functions: Python Resolver
; ==============================================================================

FindPythonExecutable() {
    ; Check for local virtual environment first
    vevnPy := A_ScriptDir "\vevn\Scripts\python.exe"
    if FileExist(vevnPy)
        return vevnPy

    venvPy := A_ScriptDir "\venv\Scripts\python.exe"
    if FileExist(venvPy)
        return venvPy

    venvPy2 := A_ScriptDir "\.venv\Scripts\python.exe"
    if FileExist(venvPy2)
        return venvPy2

    ; Default to system python
    return "python.exe"
}

; ==============================================================================
; Helper Functions: Lightweight JSON Serialization/Deserialization
; ==============================================================================

JSON_Serialize(obj) {
    if IsObject(obj) {
        if (obj is Map) {
            items := []
            for k, v in obj {
                items.Push('"' EscJson(k) '":' JSON_Serialize(v))
            }
            return "{" JoinArray(items, ",") "}"
        } else if (obj is Array) {
            items := []
            for v in obj {
                items.Push(JSON_Serialize(v))
            }
            return "[" JoinArray(items, ",") "]"
        }
    } else if (IsNumber(obj)) {
        return obj
    } else if (obj is Integer || obj is Float) {
        return obj
    } else {
        return '"' EscJson(String(obj)) '"'
    }
    return '""'
}

EscJson(str) {
    str := StrReplace(str, "\", "\\")
    str := StrReplace(str, '"', '\"')
    str := StrReplace(str, "`n", "\n")
    str := StrReplace(str, "`r", "\r")
    str := StrReplace(str, "`t", "\t")
    return str
}

JoinArray(arr, delim) {
    res := ""
    for idx, item in arr {
        res .= (idx == 1 ? "" : delim) item
    }
    return res
}

JSON_Deserialize(jsonStr) {
    try {
        mapObj := Map()
        
        if (RegExMatch(jsonStr, '"success"\s*:\s*(true|false)', &mSucc)) {
            mapObj["success"] := (mSucc[1] == "true")
        }
        if (RegExMatch(jsonStr, '"changed"\s*:\s*(true|false)', &mChg)) {
            mapObj["changed"] := (mChg[1] == "true")
        }
        
        mapObj["rewritten_text"] := ExtractJsonField(jsonStr, "rewritten_text")
        mapObj["scenario"] := ExtractJsonField(jsonStr, "scenario")
        mapObj["scenario_description"] := ExtractJsonField(jsonStr, "scenario_description")
        mapObj["error"] := ExtractJsonField(jsonStr, "error")
        
        return mapObj
    } catch {
        return ""
    }
}

ExtractJsonField(json, fieldName) {
    pattern := '"' fieldName '"\s*:\s*"(.*?)"(?=\s*[,}])'
    if (RegExMatch(json, pattern, &m)) {
        val := m[1]
        val := StrReplace(val, '\"', '"')
        val := StrReplace(val, "\\", "\")
        val := StrReplace(val, "\n", "`n")
        val := StrReplace(val, "\r", "`r")
        val := StrReplace(val, "\t", "`t")
        return val
    }
    return ""
}

LogMsg(msg) {
    logPath := A_ScriptDir "\copilot.log"
    ts := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    try FileAppend("[" ts "] " msg "`n", logPath, "UTF-8-RAW")
}

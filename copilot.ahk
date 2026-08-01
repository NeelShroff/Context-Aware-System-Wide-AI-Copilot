#Requires AutoHotkey v2.0
#SingleInstance Force

; ==============================================================================
; Context-Aware System-Wide AI Writing Copilot (Windows)
; Triggers:
; 1. Double-Tap Ctrl (Press Ctrl twice fast)
; 2. Mouse Side Button (XButton1 / Back Mouse Button)
; 3. Ctrl + Shift + P (Context Workspace Quick Search)
; 4. Ctrl + Alt + E (Legacy Fallback)
; ==============================================================================

global isProcessing := false
global statusGui := ""
global statusText := ""
global currentDomain := "AUTO"
global currentProject := "System-Wide AI Copilot"
global currentCategory := "Development"
global currentPriority := "HIGH"
global gdiplusToken := 0

try {
    si := Buffer(24, 0)
    NumPut("UInt", 1, si, 0)
    DllCall("gdiplus\GdiplusStartup", "Ptr*", &gdiplusToken, "Ptr", si, "Ptr", 0)
}

; ==============================================================================
; Native System Tray & Context Management Configuration
; ==============================================================================
Tray := A_TrayMenu
A_IconTip := "System-Wide AI Copilot (Right-Click for Menu)"
Tray.Delete()
Tray.Add("✨ System-Wide AI Copilot", (*) => "")
Tray.Disable("✨ System-Wide AI Copilot")
Tray.Add()
Tray.Add("📁 Active: " currentProject " [" currentPriority "]", PromptSetProject)
Tray.Add("🔍 Quick Search Workspaces (Ctrl+Shift+P)", PromptSearchProject)
Tray.Add("🏷️ Set Category (" currentCategory ")", PromptSetCategory)
Tray.Add("⭐ Set Priority (" currentPriority ")", PromptSetPriority)
Tray.Add()
Tray.Add("🌐 Auto-Detect Domain (Smart)", (*) => SetDomain("AUTO", "AUTO-DETECT"))
Tray.Add("💼 Work & Enterprise", (*) => SetDomain("WORK", "WORK & ENTERPRISE"))
Tray.Add("💬 Personal & Casual", (*) => SetDomain("PERSONAL", "PERSONAL & CASUAL"))
Tray.Add("💻 Development & Engineering", (*) => SetDomain("DEVELOPMENT", "DEVELOPMENT"))
Tray.Add("⚡ AI Prompt Engineering", (*) => SetDomain("PROMPT_ENGINEERING", "AI PROMPT ENG"))
Tray.Add()
Tray.Add("📊 View Knowledge Graph", (*) => Run('"' A_ScriptDir '\scripts\show_graph.cmd"'))
Tray.Add("🌐 Open Web Dashboard", (*) => Run('"' A_ScriptDir '\scripts\launch_web_dashboard.cmd"'))
Tray.Add("🕶️ Launch 3D AI Companion", PromptLaunchPet)
Tray.Add()
Tray.Add("🦊 Switch Pet: Anime Neko Cat", (*) => SetPetCharacter("NEKO", "Anime Neko Cat"))
Tray.Add("👧 Switch Pet: Chibi Assistant", (*) => SetPetCharacter("CHIBI", "Chibi Assistant"))
Tray.Add("🤖 Switch Pet: Cyber Drone Core", (*) => SetPetCharacter("DRONE", "Cyber Drone Core"))
Tray.Add("📺 Switch Pet: Cyberpunk Droid", (*) => SetPetCharacter("CYBER_BOT", "Cyberpunk Droid"))
Tray.Add("🔮 Switch Pet: Magical Flame Spirit", (*) => SetPetCharacter("MAGICAL_SPIRIT", "Magical Flame Spirit"))
Tray.Add()
Tray.Add("❌ Exit Copilot", (*) => ExitApp())
Tray.Check("🌐 Auto-Detect Domain (Smart)")

PromptLaunchPet(*) {
    Run('"' A_ScriptDir '\vevn\Scripts\python.exe" -m src.pet.vrm_pet_gui', A_ScriptDir, "Hide")
    ShowStatusToast("🕶️ 3D Companion Launching...", 2500)
}

SetPetCharacter(styleCode, styleName) {
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", "http://127.0.0.1:8799/api/character?style=" . styleCode, true)
        whr.Send()
        ShowStatusToast("🎭 Switched to: " styleName, 2000)
    } catch as err {
        ShowStatusToast("❌ Start 3D Pet first", 2000)
    }
}

PromptSetProject(*) {
    global currentProject
    ib := InputBox("Enter active Context Workspace name (e.g., Voice AI Pipeline, E-Commerce Platform):", "Context Workspace Manager", "w420 h140", currentProject)
    if (ib.Result == "OK" && Trim(ib.Value) != "") {
        currentProject := Trim(ib.Value)
        ShowStatusToast("📁 Active Workspace: " currentProject, 2500)
    }
}

PromptSearchProject(*) {
    global currentProject
    ib := InputBox("Search Workspaces or enter new Context name:", "Context Quick Search (Ctrl+Shift+P)", "w420 h140", currentProject)
    if (ib.Result == "OK" && Trim(ib.Value) != "") {
        currentProject := Trim(ib.Value)
        ShowStatusToast("🔍 Switched to Workspace: " currentProject, 2500)
    }
}

PromptSetCategory(*) {
    global currentCategory
    ib := InputBox("Set Category for active Workspace (e.g., Development, Work, Personal, AI Research):", "Workspace Category", "w420 h140", currentCategory)
    if (ib.Result == "OK" && Trim(ib.Value) != "") {
        currentCategory := Trim(ib.Value)
        ShowStatusToast("🏷️ Category: " currentCategory, 2000)
    }
}

PromptSetPriority(*) {
    global currentPriority
    ib := InputBox("Set Priority (HIGH, NORMAL, LOW):", "Workspace Priority", "w420 h140", currentPriority)
    if (ib.Result == "OK" && Trim(ib.Value) != "") {
        p := StrUpper(Trim(ib.Value))
        if (p == "HIGH" || p == "NORMAL" || p == "LOW") {
            currentPriority := p
            ShowStatusToast("⭐ Priority: " currentPriority, 2000)
        }
    }
}

SetDomain(domainCode, domainName) {
    global currentDomain := domainCode
    Tray.Uncheck("🌐 Auto-Detect Domain (Smart)")
    Tray.Uncheck("💼 Work & Enterprise")
    Tray.Uncheck("💬 Personal & Casual")
    Tray.Uncheck("💻 Development & Engineering")
    Tray.Uncheck("⚡ AI Prompt Engineering")
    
    if (domainCode == "AUTO")
        Tray.Check("🌐 Auto-Detect Domain (Smart)")
    else if (domainCode == "WORK")
        Tray.Check("💼 Work & Enterprise")
    else if (domainCode == "PERSONAL")
        Tray.Check("💬 Personal & Casual")
    else if (domainCode == "DEVELOPMENT")
        Tray.Check("💻 Development & Engineering")
    else if (domainCode == "PROMPT_ENGINEERING")
        Tray.Check("⚡ AI Prompt Engineering")
        
    ShowStatusToast("🎯 Graph Domain: " domainName, 2000)
}

; 1. Double-Tap Ctrl Trigger
~LControl:: {
    if (A_PriorHotkey == "~LControl" && A_TimeSincePriorHotkey < 400) {
        TriggerCopilot()
    }
}

; 2. Mouse Side Buttons (Supports XButton1, XButton2, Browser_Back, Browser_Forward)
$XButton1::
$XButton2::
Browser_Back::
Browser_Forward:: {
    TriggerCopilot()
}

; 3. Hotkey: Ctrl + Shift + P (Context Quick Search)
^+p:: {
    PromptSearchProject()
}

; 4. Hotkey Fallback: Ctrl + Alt + E
^!e:: {
    TriggerCopilot()
}

TriggerCopilot() {
    global isProcessing, currentDomain, currentProject, currentCategory, currentPriority
    
    ; Capture the user's active window IMMEDIATELY before any GUI/clipboard actions
    targetHwnd := WinActive("A")
    if (!targetHwnd)
        targetHwnd := WinExist("A")

    if (isProcessing) {
        ShowStatusToast("⏳ Request already in progress...", 1500)
        return
    }

    isProcessing := true

    ; Step 1: Show initial status
    ShowStatusToast("✨ Understanding Context...", 0)

    ; Step 2: Backup clipboard and capture text (Smart Auto-Select with Page Safety Limit)
    savedClipboard := ClipboardAll()
    A_Clipboard := ""

    SendInput("^c")
    if (!ClipWait(0.2)) {
        ; Auto-select text in current input box
        A_Clipboard := ""
        SendInput("^a^c")
        ClipWait(0.4)
    }

    selectedText := A_Clipboard
    
    ; Safety check: Prevent full web page selection on web apps
    if (StrLen(selectedText) > 4000) {
        LogMsg("Safety warning: Selected text exceeds 4,000 char webpage safety limit (len: " StrLen(selectedText) ")")
        SendInput("{Right}") ; Deselect web page selection
        ShowStatusToast("⚠️ Text selection too large", 2500)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    if (StrLen(Trim(selectedText)) == 0) {
        ShowStatusToast("⚠️ Select text or input box", 2000)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    LogMsg("Captured text len: " StrLen(selectedText) " snippet: '" SubStr(selectedText, 1, 40) "...'")

    ; Step 3: Capture Target Application Metadata
    activeTitle := "Unknown"
    activeProcess := "Unknown"
    activePath := "Unknown"
    activeClass := "Unknown"

    try {
        if (targetHwnd) {
            activeTitle := WinGetTitle(targetHwnd)
            activeProcess := WinGetProcessName(targetHwnd)
            activePath := WinGetProcessPath(targetHwnd)
            activeClass := WinGetClass(targetHwnd)
        }
    } catch {
        activeTitle := "Unknown"
        activeProcess := "Unknown"
        activePath := "Unknown"
        activeClass := "Unknown"
    }

    ; Step 3b: Extract Browser URL from Address Bar (Chrome, Edge, Firefox)
    activeBrowserUrl := ""
    try {
        browserProcs := ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"]
        isBrowser := false
        lowerProc := StrLower(activeProcess)
        for proc in browserProcs {
            if (InStr(lowerProc, proc)) {
                isBrowser := true
                break
            }
        }
        if (isBrowser && targetHwnd) {
            ; Try to read URL from Chrome/Edge address bar via UIA Automation
            psUrlCmd := Format('powershell -NoProfile -Command "$w = Get-Process -Id (Get-Process | Where-Object {{$_.MainWindowHandle -eq {1}}}).Id -ErrorAction SilentlyContinue; Add-Type -AssemblyName UIAutomationClient; $root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]{1}); $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit); $edit = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond); if ($edit) {{ $p = $edit.GetCurrentPropertyValue([System.Windows.Automation.AutomationElement]::NameProperty); $v = $edit.GetCurrentPropertyValue([System.Windows.Automation.ValuePattern]::ValueProperty); Write-Output $v }} else {{ Write-Output \"\" }}"', targetHwnd)
            shell2 := ComObject("WScript.Shell")
            exec2 := shell2.Exec(psUrlCmd)
            activeBrowserUrl := Trim(exec2.StdOut.ReadAll())
            ; Only keep if it looks like a URL
            if (!RegExMatch(activeBrowserUrl, "^https?://")) {
                activeBrowserUrl := ""
            }
        }
    } catch {
        activeBrowserUrl := ""
    }

    ; Step 4: Write Payload to Unique Temporary JSON File
    reqPath := A_Temp "\ai_copilot_req_" A_TickCount ".json"
    resPath := A_Temp "\ai_copilot_res_" A_TickCount ".json"
    imgPath := A_Temp "\ai_copilot_img_" A_TickCount ".png"

    try FileDelete(reqPath)
    try FileDelete(resPath)
    try FileDelete(imgPath)

    ; Check if clipboard contains an image / screenshot
    hasImage := false
    try {
        psCmd := Format('powershell -NoProfile -ExecutionPolicy Bypass -File "{1}\scripts\save_clipboard_image.ps1" "{2}"', A_ScriptDir, imgPath)
        RunWait(psCmd, A_ScriptDir, "Hide")
        if (FileExist(imgPath))
            hasImage := true
    }

    ; === Silent Native Window Screenshot (for vision context extraction — 100% native GDI, no AMSI block) ===
    screenshotPath := A_Temp "\ai_copilot_ss_" A_TickCount ".png"
    hasScreenshot := CaptureWindowScreenshot(screenshotPath, targetHwnd)
    LogMsg("Background screenshot captured: " (hasScreenshot ? "YES (" screenshotPath ")" : "NO"))

    payload := Map(
        "text", selectedText,
        "domain_override", currentDomain,
        "project_name", currentProject,
        "category", currentCategory,
        "priority", currentPriority,
        "image_path", hasImage ? imgPath : "",
        "screenshot_path", hasScreenshot ? screenshotPath : "",
        "context", Map(
            "title", activeTitle,
            "process", activeProcess,
            "path", activePath,
            "class", activeClass,
            "url", activeBrowserUrl
        )
    )

    jsonStr := JSON_Serialize(payload)
    FileAppend(jsonStr, reqPath, "UTF-8-RAW")
    LogMsg("Request written to " reqPath " (len: " StrLen(selectedText) ", domain: " currentDomain ", project: '" currentProject "', screenshot: " (hasScreenshot ? "YES" : "NO") ")")
    LogMsg("Window context: process='" activeProcess "' title='" activeTitle "' url='" activeBrowserUrl "'")

    ; Step 5: Update Status UI to Improving
    UpdateStatusToast("✨ Copilot Improving Text...")

    ; Step 6: Invoke Python Engine via helper batch file
    runnerBat := A_ScriptDir "\scripts\run_python.bat"
    cmdLine := Format('"{1}" "{2}" "{3}"', runnerBat, reqPath, resPath)
    LogMsg("Executing runner: " cmdLine)
    
    exitCode := RunWait(cmdLine, A_ScriptDir, "Hide")
    LogMsg("Runner finished with exitCode: " exitCode)

    ; Step 7: Process Result
    if (!FileExist(resPath)) {
        LogMsg("ERROR: Response file " resPath " was not created!")
        ShowStatusToast("❌ Error: Python execution failed", 3000)
        A_Clipboard := savedClipboard
        try FileDelete(reqPath)
        try FileDelete(resPath)
        try FileDelete(imgPath)
        isProcessing := false
        return
    }

    resJson := FileRead(resPath, "UTF-8-RAW")
    resultMap := JSON_Deserialize(resJson)

    if (!resultMap) {
        LogMsg("ERROR: Failed to parse JSON response: " resJson)
        ShowStatusToast("❌ Error: Invalid response format", 3000)
        A_Clipboard := savedClipboard
        try FileDelete(reqPath)
        try FileDelete(resPath)
        try FileDelete(imgPath)
        isProcessing := false
        return
    }

    if (!resultMap["success"]) {
        errMsg := resultMap.Has("error") ? resultMap["error"] : "Unknown error"
        LogMsg("ERROR: LLM returned failure: " errMsg)
        ShowStatusToast("❌ " errMsg, 3500)
        A_Clipboard := savedClipboard
        try FileDelete(reqPath)
        try FileDelete(resPath)
        try FileDelete(imgPath)
        isProcessing := false
        return
    }

    rewrittenText := resultMap["rewritten_text"]
    changed := resultMap.Has("changed") ? resultMap["changed"] : false
    scenarioDesc := resultMap.Has("scenario_description") ? resultMap["scenario_description"] : ""
    LogMsg("Success! Scenario: " scenarioDesc ", changed: " (changed ? "true" : "false") ", output len: " StrLen(rewrittenText))

    if (changed && StrLen(rewrittenText) > 0) {
        ; Step 8: Replace text selection cleanly
        KeyWait("Control")
        KeyWait("Alt")
        KeyWait("e")
        Sleep(50)

        A_Clipboard := rewrittenText
        ClipWait(0.5)
        
        SendInput("^v")
        Sleep(150)
        
        UpdateStatusToast("✅ Done (" scenarioDesc ")")
        SetTimer(HideStatusToast, -2000)
    } else {
        UpdateStatusToast("✅ Text optimal (no changes needed)")
        SetTimer(HideStatusToast, -2000)
    }

    ; Step 9: Restore Original Clipboard & Clean Up Temp Files
    Sleep(100)
    A_Clipboard := savedClipboard
    try FileDelete(reqPath)
    try FileDelete(resPath)
    try FileDelete(imgPath)
    isProcessing := false
}

; ==============================================================================
; Helper Functions: UI Toast Overlay & Margin Offset Controls
; ==============================================================================

ShowStatusToast(msg, durationMs := 0) {
    ; Route status notification directly to 3D AI Companion speech bubble
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", "http://127.0.0.1:8799/api/speech", true)
        whr.SetRequestHeader("Content-Type", "application/json")
        dur := (durationMs > 0 ? durationMs / 1000 : 4.0)
        body := '{"text":"' . StrReplace(msg, '"', '\"') . '","duration":' . dur . ',"mode":"TALKING"}'
        whr.Send(body)
    } catch {
    }
}

UpdateStatusToast(msg) {
    ShowStatusToast(msg, 3000)
}

HideStatusToast() {
}


IsFocusedControlTextInput() {
    try {
        ctrlHwnd := ControlGetFocus("A")
        if (ctrlHwnd) {
            focusedClass := WinGetClass(ctrlHwnd)
            if (RegExMatch(focusedClass, "i)(Edit|RichEdit|Scintilla|TEXTAREA|INPUT)")) {
                return true
            }
        }
    }
    return false
}

LogMsg(msg) {
    logPath := A_ScriptDir "\copilot.log"
    timeStr := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    try {
        FileAppend("[" timeStr "] " msg "`n", logPath, "UTF-8-RAW")
    }
}

; Simple JSON Serializer & Deserializer for AHK v2 Maps/Arrays
JSON_Serialize(obj) {
    if (IsObject(obj)) {
        if (obj is Map) {
            items := []
            for k, v in obj {
                items.Push('"' k '":' JSON_Serialize(v))
            }
            return "{" Join(",", items) "}"
        } else if (obj is Array) {
            items := []
            for v in obj {
                items.Push(JSON_Serialize(v))
            }
            return "[" Join(",", items) "]"
        }
    } else if (IsNumber(obj)) {
        return obj
    } else {
        str := String(obj)
        str := StrReplace(str, "\", "\\")
        str := StrReplace(str, '"', '\"')
        str := StrReplace(str, "`n", "\n")
        str := StrReplace(str, "`r", "\r")
        str := StrReplace(str, "`t", "\t")
        return '"' str '"'
    }
}

JSON_Deserialize(str) {
    try {
        psCmd := Format('powershell -NoProfile -Command "$Input | ConvertFrom-Json | ConvertTo-Json -Depth 10"')
        shell := ComObject("WScript.Shell")
        exec := shell.Exec(psCmd)
        exec.StdIn.Write(str)
        exec.StdIn.Close()
        outJson := exec.StdOut.ReadAll()
        return ParseParsedJson(outJson)
    } catch {
        return Map("success", false, "error", "JSON Parse Error")
    }
}

ParseParsedJson(jsonStr) {
    resMap := Map()
    if (RegExMatch(jsonStr, 'i)"success"\s*:\s*true'))
        resMap["success"] := true
    else
        resMap["success"] := false

    if (RegExMatch(jsonStr, 'i)"changed"\s*:\s*true'))
        resMap["changed"] := true
    else
        resMap["changed"] := false

    if (RegExMatch(jsonStr, 's)"rewritten_text"\s*:\s*"(.*?)"(?:\s*,\s*"|\s*})', &match)) {
        val := match[1]
        val := StrReplace(val, '\"', '"')
        val := StrReplace(val, '\n', "`n")
        val := StrReplace(val, '\\', "\")
        val := DecodeUnicodeEscapes(val)  ; Fix \u0027 → ' etc
        resMap["rewritten_text"] := val
    }

    if (RegExMatch(jsonStr, 's)"scenario_description"\s*:\s*"(.*?)"(?:\s*,\s*"|\s*})', &matchScen)) {
        resMap["scenario_description"] := matchScen[1]
    }

    if (RegExMatch(jsonStr, 's)"error"\s*:\s*"(.*?)"(?:\s*,\s*"|\s*})', &matchErr)) {
        resMap["error"] := matchErr[1]
    }

    return resMap
}

Join(sep, arr) {
    str := ""
    for idx, item in arr {
        str .= (idx > 1 ? sep : "") item
    }
    return str
}

DecodeUnicodeEscapes(str) {
    ; Convert raw \uXXXX escape sequences to actual Unicode characters
    ; e.g. \u0027 → ', \u2019 → ', \u00e9 → é
    result := ""
    i := 1
    while (i <= StrLen(str)) {
        if (SubStr(str, i, 2) == "\u" && i + 5 <= StrLen(str)) {
            hexPart := SubStr(str, i + 2, 4)
            if (RegExMatch(hexPart, "^[0-9a-fA-F]{4}$")) {
                result .= Chr(Integer("0x" hexPart))
                i += 6
                continue
            }
        }
        result .= SubStr(str, i, 1)
        i++
    }
    return result
}

CaptureWindowScreenshot(outputPath, hwnd := 0) {
    try {
        ; Always use full screen bounds for reliable capture
        left := 0
        top := 0
        w := A_ScreenWidth
        h := A_ScreenHeight

        ; Initialize GDI+ locally for this call
        localToken := 0
        si := Buffer(24, 0)
        NumPut("UInt", 1, si, 0)
        if (DllCall("gdiplus\GdiplusStartup", "Ptr*", &localToken, "Ptr", si, "Ptr", 0) != 0) {
            LogMsg("CaptureWindowScreenshot: GdiplusStartup FAILED")
            return false
        }

        hdcScreen := DllCall("user32\GetDC", "Ptr", 0, "Ptr")
        hdcMem := DllCall("gdi32\CreateCompatibleDC", "Ptr", hdcScreen, "Ptr")
        hbm := DllCall("gdi32\CreateCompatibleBitmap", "Ptr", hdcScreen, "Int", w, "Int", h, "Ptr")
        obm := DllCall("gdi32\SelectObject", "Ptr", hdcMem, "Ptr", hbm, "Ptr")

        DllCall("gdi32\BitBlt", "Ptr", hdcMem, "Int", 0, "Int", 0, "Int", w, "Int", h, "Ptr", hdcScreen, "Int", left, "Int", top, "UInt", 0x00CC0020)

        pBitmap := 0
        gdipRet := DllCall("gdiplus\GdipCreateBitmapFromHBITMAP", "Ptr", hbm, "Ptr", 0, "Ptr*", &pBitmap)
        if (pBitmap == 0 || gdipRet != 0) {
            LogMsg("CaptureWindowScreenshot: GdipCreateBitmapFromHBITMAP FAILED ret=" gdipRet " pBitmap=" pBitmap)
            DllCall("gdi32\SelectObject", "Ptr", hdcMem, "Ptr", obm)
            DllCall("gdi32\DeleteObject", "Ptr", hbm)
            DllCall("gdi32\DeleteDC", "Ptr", hdcMem)
            DllCall("user32\ReleaseDC", "Ptr", 0, "Ptr", hdcScreen)
            DllCall("gdiplus\GdiplusShutdown", "Ptr", localToken)
            return false
        }

        ; CLSID PNG: {557CF406-1A04-11D3-9A73-0000F81EF32E}
        clsidPNG := Buffer(16, 0)
        NumPut("UInt", 0x557CF406, clsidPNG, 0)
        NumPut("UShort", 0x1A04, clsidPNG, 4)
        NumPut("UShort", 0x11D3, clsidPNG, 6)
        NumPut("UChar", 0x9A, clsidPNG, 8)
        NumPut("UChar", 0x73, clsidPNG, 9)
        NumPut("UChar", 0x00, clsidPNG, 10)
        NumPut("UChar", 0x00, clsidPNG, 11)
        NumPut("UChar", 0xF8, clsidPNG, 12)
        NumPut("UChar", 0x1E, clsidPNG, 13)
        NumPut("UChar", 0xF3, clsidPNG, 14)
        NumPut("UChar", 0x2E, clsidPNG, 15)

        status := DllCall("gdiplus\GdipSaveImageToFile", "Ptr", pBitmap, "WStr", outputPath, "Ptr", clsidPNG, "Ptr", 0)

        DllCall("gdiplus\GdipDisposeImage", "Ptr", pBitmap)
        DllCall("gdi32\SelectObject", "Ptr", hdcMem, "Ptr", obm)
        DllCall("gdi32\DeleteObject", "Ptr", hbm)
        DllCall("gdi32\DeleteDC", "Ptr", hdcMem)
        DllCall("user32\ReleaseDC", "Ptr", 0, "Ptr", hdcScreen)
        DllCall("gdiplus\GdiplusShutdown", "Ptr", localToken)

        ok := (status == 0 && FileExist(outputPath))
        LogMsg("CaptureWindowScreenshot: status=" status " file=" outputPath " exists=" (FileExist(outputPath) ? "YES" : "NO"))
        return ok
    } catch as err {
        LogMsg("CaptureWindowScreenshot exception: " err.Message " at line " err.Line)
        return false
    }
}


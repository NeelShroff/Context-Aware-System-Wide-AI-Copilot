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
Tray.Add("🎙️ Voice Dictation (Ctrl+Shift+V)", (*) => TriggerVoiceDictation())
Tray.Add("💬 Open AI Chatbot (Ctrl+Alt+C)", OpenChatWindow)
Tray.Add("📊 View Knowledge Graph (Neo4j)", (*) => Run("http://localhost:7474"))
Tray.Add("🕶️ Launch 3D AI Companion", PromptLaunchPet)
Tray.Add()
Tray.Add("🦊 Switch Pet: Anime Neko Cat", (*) => SetPetCharacter("NEKO", "Anime Neko Cat"))
Tray.Add("👧 Switch Pet: Chibi Assistant", (*) => SetPetCharacter("CHIBI", "Chibi Assistant"))
Tray.Add("🤖 Switch Pet: Cyber Drone Core", (*) => SetPetCharacter("DRONE", "Cyber Drone Core"))
Tray.Add("📺 Switch Pet: Cyberpunk Droid", (*) => SetPetCharacter("CYBER_BOT", "Cyberpunk Droid"))
Tray.Add("🔮 Switch Pet: Magical Flame Spirit", (*) => SetPetCharacter("MAGICAL_SPIRIT", "Magical Flame Spirit"))
Tray.Add()
Tray.Add("🚀 Auto-Start on Laptop Boot", ToggleAutoStart)
Tray.Add()
Tray.Add("❌ Exit Copilot", (*) => ExitApp())

Tray.Check("🌐 Auto-Detect Domain (Smart)")

; Check current startup state on launch
try {
    ret := RunWait('"' A_ScriptDir '\vevn\Scripts\python.exe" "' A_ScriptDir '\scripts\manage_startup.py" --status', A_ScriptDir, "Hide")
    ; if stdout check needed or simple check
}

ToggleAutoStart(*) {
    try {
        RunWait('"' A_ScriptDir '\vevn\Scripts\python.exe" "' A_ScriptDir '\scripts\manage_startup.py" --toggle', A_ScriptDir, "Hide")
        ShowStatusToast("🚀 Auto-Start Setting Updated", 2500)
    } catch {
        ShowStatusToast("❌ Failed to update Auto-Start", 2500)
    }
}

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

; 5. Hotkey: Ctrl + Alt + C (Open AI Chatbot)
^!c:: {
    OpenChatWindow()
}

; 6. Hotkey: Ctrl + Shift + V (Voice Dictation)
^+v:: {
    TriggerVoiceDictation()
}

OpenChatWindow(*) {
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", "http://127.0.0.1:8799/api/chat/open", true)
        whr.Send()
    } catch {
    }
}

TriggerVoiceDictation(*) {
    global isProcessing, currentDomain, currentProject, currentCategory, currentPriority
    
    targetHwnd := WinActive("A")
    if (!targetHwnd)
        targetHwnd := WinExist("A")

    if (isProcessing) {
        ShowStatusToast("⏳ Request already in progress...", 1500)
        return
    }

    isProcessing := true
    ShowStatusToast("🎙️ Listening... (Speak into mic)", 0)

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

    activeBrowserUrl := ""
    lowerProc := StrLower(activeProcess)
    if (InStr(lowerProc, "chrome") || InStr(lowerProc, "msedge") || InStr(lowerProc, "firefox") || InStr(lowerProc, "brave") || InStr(lowerProc, "opera")) {
        activeBrowserUrl := activeTitle
    }

    reqPath := A_Temp "\ai_copilot_voice_req_" A_TickCount ".json"
    resPath := A_Temp "\ai_copilot_voice_res_" A_TickCount ".json"

    try FileDelete(reqPath)
    try FileDelete(resPath)

    screenshotPath := A_Temp "\ai_copilot_voice_ss_" A_TickCount ".png"
    hasScreenshot := CaptureWindowScreenshot(screenshotPath, targetHwnd)
    LogMsg("Voice screenshot captured: " (hasScreenshot ? "YES (" screenshotPath ")" : "NO"))

    payload := Map(
        "is_voice", true,
        "text", "",
        "max_seconds", 12.0,
        "domain_override", currentDomain,
        "project_name", currentProject,
        "category", currentCategory,
        "priority", currentPriority,
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
    resultMap := ""

    ; Fast-Path HTTP Request to in-memory Python Engine
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", "http://127.0.0.1:8799/api/copilot", false)
        whr.SetRequestHeader("Content-Type", "application/json; charset=utf-8")
        whr.Send(jsonStr)
        if (whr.Status == 200) {
            resJson := whr.ResponseText
            resultMap := JSON_Deserialize(resJson)
        }
    } catch as err {
    }

    ; Fallback headless python execution
    if (!resultMap) {
        pyExe := A_ScriptDir "\vevn\Scripts\pythonw.exe"
        if (!FileExist(pyExe))
            pyExe := "pythonw.exe"

        FileAppend(jsonStr, reqPath, "UTF-8-RAW")
        cmdLine := pyExe ' "' A_ScriptDir '\src\main.py" "' reqPath '" "' resPath '"'
        RunWait(cmdLine, A_ScriptDir, "Hide")

        if (FileExist(resPath)) {
            resJson := FileRead(resPath, "UTF-8-RAW")
            resultMap := JSON_Deserialize(resJson)
        }
    }

    if (!resultMap || !resultMap.Has("success") || !resultMap["success"]) {
        errMsg := (resultMap && resultMap.Has("error")) ? resultMap["error"] : "Voice dictation failed"
        ShowStatusToast("❌ " errMsg, 3500)
        try FileDelete(reqPath)
        try FileDelete(resPath)
        isProcessing := false
        return
    }

    scenario := resultMap.Has("scenario") ? resultMap["scenario"] : ""
    bubbleMsg := resultMap.Has("bubble_message") ? resultMap["bubble_message"] : ""
    rewrittenText := resultMap.Has("rewritten_text") ? resultMap["rewritten_text"] : ""
    lowerRewritten := StrLower(rewrittenText)

    isAction := (scenario == "MUSIC_CONTROL" || scenario == "REMINDER_SET" || scenario == "MEMORY_FACT_SAVED"
        || InStr(lowerRewritten, "now playing:")
        || InStr(lowerRewritten, "music stopped")
        || InStr(lowerRewritten, "music paused")
        || InStr(lowerRewritten, "music resumed")
        || InStr(lowerRewritten, "reminder set")
        || InStr(lowerRewritten, "saved fact")
        || InStr(lowerRewritten, "saved memory"))

    if (isAction) {
        toastMsg := (StrLen(Trim(bubbleMsg)) > 0) ? bubbleMsg : rewrittenText
        ShowStatusToast("✨ " . toastMsg, 3500)
        try FileDelete(reqPath)
        try FileDelete(resPath)
        isProcessing := false
        return
    }


    rewrittenText := resultMap.Has("rewritten_text") ? resultMap["rewritten_text"] : ""
    if (StrLen(Trim(rewrittenText)) > 0) {
        savedClipboard := ClipboardAll()
        A_Clipboard := rewrittenText
        ClipWait(0.5)
        
        SendInput("^v")

        
        if (InStr(lowerProc, "winword") || InStr(lowerProc, "excel") || InStr(lowerProc, "powerpnt") || InStr(lowerProc, "outlook")) {
            Sleep(450)
        } else {
            Sleep(250)
        }

        UpdateStatusToast("🎙️ Voice Dictation Pasted!")
        SetTimer(HideStatusToast, -2000)

        if (savedClipboard != "") {
            try {
                A_Clipboard := savedClipboard
            } catch {
            }
        }
    } else {
        ShowStatusToast("❌ No speech recognized", 2500)
    }

    try FileDelete(reqPath)
    try FileDelete(resPath)
    isProcessing := false
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

    ; Step 1: Show initial status quip
    quips := ["Analyzing context...", "Reading active window...", "Processing request...", "Enhancing text..."]
    quip := quips[Random(1, quips.Length)]
    ShowStatusToast(quip, 0)

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
        ShowStatusToast("Text selection too large", 2500)
        A_Clipboard := savedClipboard
        isProcessing := false
        return
    }

    if (StrLen(Trim(selectedText)) == 0) {
        ShowStatusToast("Select text or input box", 2000)
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

    ; Step 3b: Extract Browser URL from Title (0ms cost, zero subprocesses)
    activeBrowserUrl := ""
    lowerProc := StrLower(activeProcess)
    if (InStr(lowerProc, "chrome") || InStr(lowerProc, "msedge") || InStr(lowerProc, "firefox") || InStr(lowerProc, "brave") || InStr(lowerProc, "opera")) {
        activeBrowserUrl := activeTitle
    }

    ; Step 4: Write Payload to Unique Temporary JSON File
    reqPath := A_Temp "\ai_copilot_req_" A_TickCount ".json"
    resPath := A_Temp "\ai_copilot_res_" A_TickCount ".json"
    imgPath := A_Temp "\ai_copilot_img_" A_TickCount ".png"

    try FileDelete(reqPath)
    try FileDelete(resPath)
    try FileDelete(imgPath)

    ; Check if clipboard contains an image format (CF_BITMAP=2, CF_DIB=8) natively without spawning PowerShell
    ; Native clipboard image check — CF_BITMAP=2, CF_DIB=8 (0ms, zero processes)
    hasImage := (DllCall("IsClipboardFormatAvailable", "UInt", 2) || DllCall("IsClipboardFormatAvailable", "UInt", 8)) ? true : false

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
    ; NOTE: FileAppend to reqPath happens only inside the fallback block below (not needed for fast-path HTTP)
    LogMsg("Payload ready (len: " StrLen(selectedText) ", domain: " currentDomain ", project: '" currentProject "', screenshot: " (hasScreenshot ? "YES" : "NO") ")")

    ; Step 5: Update Status UI to Improving
    UpdateStatusToast("Processing context...")

    resultMap := ""
    resJson := ""

    ; Fast-Path: Direct HTTP Request to in-memory Python Engine (0ms process creation)
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", "http://127.0.0.1:8799/api/copilot", false) ; Synchronous mode
        whr.SetRequestHeader("Content-Type", "application/json; charset=utf-8")
        whr.Send(jsonStr)
        if (whr.Status == 200) {
            resJson := whr.ResponseText
            resultMap := JSON_Deserialize(resJson)
            LogMsg("Fast-path HTTP response received successfully")
        }
    } catch as err {
        LogMsg("Fast-path HTTP request unavailable: " err.Message)
    }

    ; Fallback: Direct headless pythonw.exe execution (Zero conhost / cmd window allocated)
    if (!resultMap) {
        pyExe := A_ScriptDir "\vevn\Scripts\pythonw.exe"
        if (!FileExist(pyExe))
            pyExe := "pythonw.exe"

        ; Write request JSON to disk only for the fallback path (fast-path uses in-memory HTTP)
        FileAppend(jsonStr, reqPath, "UTF-8-RAW")
        cmdLine := pyExe ' "' A_ScriptDir '\src\main.py" "' reqPath '" "' resPath '"'
        LogMsg("Executing fallback silent runner: " cmdLine)
        RunWait(cmdLine, A_ScriptDir, "Hide")

        if (FileExist(resPath)) {
            resJson := FileRead(resPath, "UTF-8-RAW")
            resultMap := JSON_Deserialize(resJson)
        }
    }

    ; Step 7: Process Result
    if (!resultMap) {
        LogMsg("ERROR: Response was not generated!")
        ShowStatusToast("Copilot execution failed", 3000)
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
        ShowStatusToast(errMsg, 3500)
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
        
        ; Allow target application (Word / Office / RichEdit) to finish reading clipboard OLE object
        if (InStr(lowerProc, "winword") || InStr(lowerProc, "excel") || InStr(lowerProc, "powerpnt") || InStr(lowerProc, "outlook")) {
            Sleep(450)
        } else {
            Sleep(250)
        }
        
        bubbleMsg := resultMap.Has("bubble_message") ? resultMap["bubble_message"] : "Text enhanced"
        UpdateStatusToast(bubbleMsg)
        SetTimer(HideStatusToast, -2000)
    } else {
        UpdateStatusToast("Text already optimal")
        SetTimer(HideStatusToast, -2000)
    }

    ; Step 9: Restore Original Clipboard safely
    if (savedClipboard != "") {
        try {
            A_Clipboard := savedClipboard
        } catch {
        }
    }
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
    ; Fire-and-forget async with short timeout so it never blocks the main flow
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("POST", "http://127.0.0.1:8799/api/speech", true) ; async
        whr.SetTimeouts(500, 500, 500, 500) ; 500ms resolve/connect/send/receive — fail fast
        whr.SetRequestHeader("Content-Type", "application/json")
        dur := (durationMs > 0 ? durationMs / 1000 : 4.0)
        body := '{"text":"' . StrReplace(msg, '"', '\"') . '","duration":' . dur . ',"mode":"TALKING"}'
        whr.Send(body)
        ; Do NOT call WaitForResponse — fire-and-forget intentional
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
    return ParseParsedJson(str)
}

ParseParsedJson(jsonStr) {
    resMap := Map()
    resMap["success"] := (InStr(jsonStr, '"success": true') || InStr(jsonStr, '"success":true')) ? true : false
    resMap["changed"] := (InStr(jsonStr, '"changed": true') || InStr(jsonStr, '"changed":true')) ? true : false

    rewrittenText := ExtractJsonString(jsonStr, "rewritten_text")
    if (rewrittenText != "")
        resMap["rewritten_text"] := rewrittenText

    scenDesc := ExtractJsonString(jsonStr, "scenario_description")
    if (scenDesc != "")
        resMap["scenario_description"] := scenDesc

    bubMsg := ExtractJsonString(jsonStr, "bubble_message")
    if (bubMsg != "")
        resMap["bubble_message"] := bubMsg

    errMsg := ExtractJsonString(jsonStr, "error")
    if (errMsg != "")
        resMap["error"] := errMsg

    return resMap
}

ExtractJsonString(jsonStr, key) {
    pos := InStr(jsonStr, '"' key '"')
    if (pos == 0)
        return ""
    valPos := InStr(jsonStr, ':', false, pos)
    if (valPos == 0)
        return ""
    quoteStart := InStr(jsonStr, '"', false, valPos)
    if (quoteStart == 0)
        return ""
    
    idx := quoteStart + 1
    len := StrLen(jsonStr)
    while (idx <= len) {
        ch := SubStr(jsonStr, idx, 1)
        if (ch == '"' && SubStr(jsonStr, idx - 1, 1) != "\") {
            break
        }
        idx++
    }
    rawVal := SubStr(jsonStr, quoteStart + 1, idx - quoteStart - 1)
    val := StrReplace(rawVal, '\"', '"')
    val := StrReplace(val, '\n', "`n")
    val := StrReplace(val, '\r', "")
    val := StrReplace(val, '\\', "\")
    return DecodeUnicodeEscapes(val)
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

        ; Reuse global GDI+ token initialized at startup — avoids per-call GdiplusStartup overhead
        global gdiplusToken
        if (gdiplusToken == 0) {
            LogMsg("CaptureWindowScreenshot: global GDI+ token not initialized")
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
        ; No GdiplusShutdown here — global token stays alive for the process lifetime

        ok := (status == 0 && FileExist(outputPath))
        LogMsg("CaptureWindowScreenshot: status=" status " file=" outputPath " exists=" (FileExist(outputPath) ? "YES" : "NO"))
        return ok
    } catch as err {
        LogMsg("CaptureWindowScreenshot exception: " err.Message " at line " err.Line)
        return false
    }
}


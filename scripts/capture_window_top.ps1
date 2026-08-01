# Silent background screenshot of the active foreground window's top header
# Usage: powershell -File capture_window_top.ps1 "C:\output.png" 150
param(
    [string]$OutputPath,
    [int]$CaptureHeight = 0
)

Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

try {
    $hwnd = [WinAPI]::GetForegroundWindow()
    $rect = New-Object WinAPI+RECT
    [WinAPI]::GetWindowRect($hwnd, [ref]$rect) | Out-Null

    $width  = $rect.Right  - $rect.Left
    $fullHeight = $rect.Bottom - $rect.Top

    # Fallback to Primary Screen if foreground window has invalid bounds
    if ($width -le 10 -or $fullHeight -le 10) {
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $rect.Left = $screen.Left
        $rect.Top = $screen.Top
        $width = $screen.Width
        $fullHeight = $screen.Height
    }

    $height = if ($CaptureHeight -gt 0) { [Math]::Min($CaptureHeight, $fullHeight) } else { $fullHeight }

    if ($width -gt 10 -and $height -gt 10) {
        $maxWidth = 1000
        if ($width -gt $maxWidth) {
            $scale = $maxWidth / $width
            $newW = [int]($width * $scale)
            $newH = [int]($height * $scale)
        } else {
            $newW = $width
            $newH = $height
        }

        $bmp = New-Object System.Drawing.Bitmap($width, $height)
        $gfx = [System.Drawing.Graphics]::FromImage($bmp)
        $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, [System.Drawing.Size]::new($width, $height))
        $gfx.Dispose()

        # Rescale and encode as lightweight JPEG (fixes Groq 400 payload limit)
        $scaledBmp = New-Object System.Drawing.Bitmap($bmp, $newW, $newH)
        $bmp.Dispose()

        $jpegCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
        $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
        $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]75)

        $scaledBmp.Save($OutputPath, $jpegCodec, $encoderParams)
        $scaledBmp.Dispose()
        Write-Output "OK"
    } else {
        Write-Output "FAIL:invalid dimensions"
    }
} catch {
    Write-Output "FAIL:$_"
}

Add-Type -Assembly System.Windows.Forms, System.Drawing
if ([System.Windows.Forms.Clipboard]::ContainsImage()) {
    $img = [System.Windows.Forms.Clipboard]::GetImage()
    $img.Save($args[0], [System.Drawing.Imaging.ImageFormat]::Png)
}

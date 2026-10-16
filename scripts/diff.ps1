# Pixel diff between two images; returns JSON report.
# Usage: powershell -NoProfile -File diff.ps1 -A <png> -B <png> [-Threshold 16]
param(
    [Parameter(Mandatory=$true)][string]$A,
    [Parameter(Mandatory=$true)][string]$B,
    [int]$Threshold = 16
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

function Load-Bitmap([string]$path) {
    if (-not (Test-Path $path)) { throw "ui_diff: file not found: $path" }
    $full = (Resolve-Path $path).Path
    $bytes = [System.IO.File]::ReadAllBytes($full)
    $ms = New-Object System.IO.MemoryStream(,$bytes)
    return [System.Drawing.Bitmap]::FromStream($ms)
}

$bmpA = Load-Bitmap $A
$bmpB = Load-Bitmap $B

try {
    if ($bmpA.Width -ne $bmpB.Width -or $bmpA.Height -ne $bmpB.Height) {
        $resized = New-Object System.Drawing.Bitmap($bmpA.Width, $bmpA.Height)
        $g = [System.Drawing.Graphics]::FromImage($resized)
        try { $g.DrawImage($bmpB, 0, 0, $bmpA.Width, $bmpA.Height) }
        finally { $g.Dispose() }
        $bmpB.Dispose()
        $bmpB = $resized
    }

    $w = $bmpA.Width
    $h = $bmpA.Height
    $total = $w * $h
    $changed = 0

    $rect = New-Object System.Drawing.Rectangle(0, 0, $w, $h)
    $fmt = [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    $dataA = $bmpA.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, $fmt)
    $dataB = $bmpB.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, $fmt)

    $rowBytes = $w * 4
    $bufA = New-Object byte[] ($rowBytes)
    $bufB = New-Object byte[] ($rowBytes)

    try {
        for ($y = 0; $y -lt $h; $y++) {
            [System.Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($dataA.Scan0, [int]($y * $dataA.Stride)), $bufA, 0, $rowBytes)
            [System.Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($dataB.Scan0, [int]($y * $dataB.Stride)), $bufB, 0, $rowBytes)
            for ($x = 0; $x -lt $rowBytes; $x += 4) {
                $ra = $bufA[$x + 2]; $ga = $bufA[$x + 1]; $ba = $bufA[$x]
                $rb = $bufB[$x + 2]; $gb = $bufB[$x + 1]; $bb = $bufB[$x]
                if ([math]::Abs($ra - $rb) -gt $Threshold -or [math]::Abs($ga - $gb) -gt $Threshold -or [math]::Abs($ba - $bb) -gt $Threshold) {
                    $changed++
                }
            }
        }
    } finally {
        $bmpA.UnlockBits($dataA)
        $bmpB.UnlockBits($dataB)
    }

    $ratio = if ($total -gt 0) { $changed / $total } else { 0 }
    $pct = [math]::Round($ratio * 100, 4)

    [pscustomobject]@{
        changed = $changed
        total = $total
        ratio = [math]::Round($ratio, 6)
        percent = $pct
        threshold = $Threshold
    } | ConvertTo-Json -Compress
} finally {
    $bmpA.Dispose()
    $bmpB.Dispose()
}

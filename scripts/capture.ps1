# DPI-aware virtual-screen capture (same technique as dsh-vision-router).
# Usage: powershell -NoProfile -NonInteractive -STA -File capture.ps1 -Output <png>
param(
    [Parameter(Mandatory=$true)][string]$Output
)

$ErrorActionPreference = 'Stop'

$source = @'
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public static class DshVisionToolkitCapture
{
    private static readonly IntPtr PerMonitorV2 = new IntPtr(-4);
    private static readonly IntPtr PerMonitorV1 = new IntPtr(-3);

    [DllImport("user32.dll")]
    private static extern IntPtr SetThreadDpiAwarenessContext(IntPtr dpiContext);

    private static IntPtr TrySetContext(IntPtr context)
    {
        try { return SetThreadDpiAwarenessContext(context); }
        catch { return IntPtr.Zero; }
    }

    private static IntPtr EnterPerMonitorContext()
    {
        IntPtr previous = TrySetContext(PerMonitorV2);
        if (previous == IntPtr.Zero) { previous = TrySetContext(PerMonitorV1); }
        if (previous == IntPtr.Zero)
        {
            throw new InvalidOperationException("could not enter a per-monitor DPI awareness context");
        }
        return previous;
    }

    private static void RestoreContext(IntPtr previous)
    {
        try { SetThreadDpiAwarenessContext(previous); } catch { }
    }

    public static void Capture(string outputPath)
    {
        IntPtr previous = EnterPerMonitorContext();
        try
        {
            Rectangle bounds = SystemInformation.VirtualScreen;
            if (bounds.Width <= 0 || bounds.Height <= 0)
            {
                throw new InvalidOperationException("the Windows virtual screen has no drawable area");
            }
            using (var bitmap = new Bitmap(bounds.Width, bounds.Height))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.CopyFromScreen(bounds.X, bounds.Y, 0, 0, bounds.Size);
                bitmap.Save(outputPath, System.Drawing.Imaging.ImageFormat.Png);
            }
        }
        finally
        {
            RestoreContext(previous);
        }
    }
}
'@

Add-Type -AssemblyName System.Windows.Forms,System.Drawing
try
{
    Add-Type -TypeDefinition $source -ReferencedAssemblies 'System.Windows.Forms.dll','System.Drawing.dll' -ErrorAction Stop
}
catch
{
    throw ("ui_screenshot: failed to initialize the DPI-aware capture helper: " + $_.Exception.Message)
}

[DshVisionToolkitCapture]::Capture($Output)
Write-Output "OK $Output"

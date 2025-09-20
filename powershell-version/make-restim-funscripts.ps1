param (
    [string]$Filename  # Base filename without extension
)

# Define the source and target filenames
$SourceFile = "$Filename.funscript"
$TargetFile1 = "$Filename.volume.funscript"
$TargetFile2 = "$Filename.frequency.funscript"
$TargetFile3 = "$Filename.pulse_frequency.funscript"
$TargetFile4 = "$Filename.pulse_width.funscript"
$TargetFile5 = "$Filename.pulse_rise_time.funscript"
$TargetFile6 = "$Filename.ramp.funscript"

# Perform the copy operations
Copy-Item -Path $SourceFile -Destination $TargetFile1 
Copy-Item -Path $SourceFile -Destination $TargetFile2 
Copy-Item -Path $SourceFile -Destination $TargetFile3 
Copy-Item -Path $SourceFile -Destination $TargetFile4 
Copy-Item -Path $SourceFile -Destination $TargetFile5
Copy-Item -Path $SourceFile -Destination $TargetFile6

Write-Host "Files copied successfully"

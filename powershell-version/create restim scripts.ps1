param (
    [string]$Filename,                       #source funscript
    [string]$SpeedWindowSizeInSeconds = 3,   # Additional parameter to pass
    [string]$AccelWindowSizeInSeconds = 3,   # Additional parameter to pass    
    [string]$VolumeRampCombineRatio = 4,    # Additional parameter to pass    
    [string]$FrequencyRampCombineRatio = 2,     # Additional parameter to pass        
    [string]$PulseWidthCombineRatio = 2,     # Additional parameter to pass    
    [string]$PulseFrequencyCombineRatio = 2     # Additional parameter to pass
)

$filenameOnly = [System.IO.Path]::GetFileNameWithoutExtension($Filename)

# Get ramp if available
$rampPath = [System.IO.Path]::ChangeExtension($Filename, ".ramp.funscript")
if (Test-Path $rampPath) {
    # ramp exists
    Copy-Item -Path $rampPath -Destination "$filenameOnly.ramp.funscript"
}
else {
    Write-Output "ramp not found"
}


# Get speed if available
$speedPath = [System.IO.Path]::ChangeExtension($Filename, ".speed.funscript")
if (Test-Path $speedPath) {
    # speed exists
    Copy-Item -Path $speedPath -Destination "$filenameOnly.speed.funscript"
}
else {
    Write-Output "speed not found"
}

# Get alpha if available
$alphaPath = [System.IO.Path]::ChangeExtension($Filename, ".alpha.funscript")
if (Test-Path $alphaPath) {
    # alpha exists
    Copy-Item -Path $alphaPath -Destination "$filenameOnly.alpha.funscript"
}
else {
    Write-Output "alpha not found"
}

# Define the full filenames with extensions
$File1 = "$Filename"
$File2 = "$filenameOnly.speed.funscript"

if (-Not (Test-Path $File2)) {
    # speed does NOT exist
    python convert-to-speed.py $File1 $File2 $SpeedWindowSizeInSeconds
}
else {
    Write-Output "speed already exists."
}



$File1 = "$filenameOnly.speed.funscript"
$File2 = "$filenameOnly.accel.funscript"

if (-Not (Test-Path $File2)) {
    # speed does NOT exist
    # Call the Python script with the constructed arguments
    python convert-to-speed.py $File1 $File2 $AccelWindowSizeInSeconds
}
else {
    Write-Output "accel already exists."
}


$File1 = "$Filename"
$File2 = "$filenameOnly.ramp.funscript"

if (-Not (Test-Path $File2)) {
    # speed does NOT exist
    # Call the Python script with the constructed arguments
    python make-volume-ramp.py $File1 $File2
}
else {
    Write-Output "ramp already exists."
}


$File1 = "$filenameOnly.ramp.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.pulse_frequency.funscript"

if (-Not (Test-Path $File3)) {
    # pulse_frequency does NOT exist
    python combine-funscripts.py $File1 $File2 $File3 $PulseFrequencyCombineRatio
}
else {
    Write-Output "pulse_frequency already exists."
}


$File1 = "$filenameOnly.alpha.funscript"
if (Test-Path $File1) {
  $File2 = "$filenameOnly.alpha-prostate.funscript"
  if (-Not (Test-Path $File2)) {
      # alpha inverted does NOT exist
      # Call the Python script with the constructed arguments
      python invert.py $File1    
      Copy-Item -Path "$filenameOnly.alpha_inverted.funscript" -Destination "$File2"    
  }
  else {
      Write-Output "alpha_inverted already exists."
  }
}



$File1 = $File3
$File2 = "$filenameOnly.pulse_frequency_inverted.funscript"
if (-Not (Test-Path $File2)) {
    # pulse_frequency_inverted does NOT exist
    # Call the Python script with the constructed arguments
    python invert.py $File1
}
else {
    Write-Output "pulse_frequency_inverted already exists."
}

$File1 = "$filenameOnly.ramp.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.volume-prostate.funscript"

if (-Not (Test-Path $File3)) {
    # volume does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File1 $File2 $File3 ($VolumeRampCombineRatio * 2) --preserve_zero
}
else {
    Write-Output "volume-prostate already exists."
}

$File1 = "$filenameOnly.ramp.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.volume.funscript"

if (-Not (Test-Path $File3)) {
    # volume does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File1 $File2 $File3 $VolumeRampCombineRatio --preserve_zero
}
else {
    Write-Output "volume already exists."
}


$File1 = $File3
$File2 = "$filenameOnly.volume_normalized.funscript"
$File3 = "$filenameOnly.volume_not_normalized.funscript"
if (-Not (Test-Path $File2)) {
    # volume_normalized does NOT exist
    # Call the Python script with the constructed arguments
    python normalize-funscript.py $File1
    Copy-Item -Path $File1 -Destination "$File3"    
    Copy-Item -Path $File2 -Destination "$File1"
}
else {
    Write-Output "volume_normalized already exists."
}

$File1 = $File1
$File2 = "$filenameOnly.volume_inverted.funscript"
if (-Not (Test-Path $File2)) {
    # volume_inverted does NOT exist
    # Call the Python script with the constructed arguments
    python invert.py $File1
}
else {
    Write-Output "volume_inverted already exists."
}


$File1 = $File2
$File2 = "$filenameOnly.pulse_rise_time.funscript"
if (-Not (Test-Path $File2)) {
    # pulse_rise_time does NOT exist
    Copy-Item -Path $File1 -Destination $File2 
}
else {
    Write-Output "pulse_rise_time already exists."
}



$File1 = "$filenameOnly.ramp.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.frequency.funscript"

if (-Not (Test-Path $File3)) {
    # frequency does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File1 $File2 $File3 $FrequencyRampCombineRatio
}
else {
    Write-Output "frequency already exists."
}

$File1 = $File3
$File2 = "$filenameOnly.frequency_inverted.funscript"
if (-Not (Test-Path $File2)) {
    # frequency_inverted does NOT exist
    # Call the Python script with the constructed arguments
    python invert.py $File1
}
else {
    Write-Output "frequency_inverted already exists."
}


$File1 = "$filenameOnly.pulse_frequency_inverted.funscript"
$File2 = "$filenameOnly.accel.funscript"
$File3 = "$filenameOnly.pulse_width.funscript"

if (-Not (Test-Path $File3)) {
    # pulse_width does NOT exist
    python combine-funscripts.py $File1 $File2 $File3 $PulseWidthCombineRatio
}
else {
    Write-Output "pulse_width already exists."
}

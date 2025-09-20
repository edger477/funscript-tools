param (
    [string]$Filename,                       #source funscript
	[double]$rest_level = 0.4,				 #level of signal when volume ramp or speed is 0
    [string]$FreqMapMin = 0.30,              #minimum to map alpha tcode to pulse_frequency tcode
    [string]$FreqMapMax = 0.95,              #maximum to map alpha tcode to pulse_frequency tcode    
    [string]$WidthLimitMin = 0.1,            #minimum to limit inverted alpha tcode to pulse_width tcode
    [string]$WidthLimitMax = 0.75,           #maximum to limit inverted alpha tcode to pulse_width tcode
    [string]$SpeedWindowSizeInSeconds = 5,   # Additional parameter to pass
    [string]$AccelWindowSizeInSeconds = 3,   # Additional parameter to pass    
    [string]$VolumeRampCombineRatio = 6,    # Additional parameter to pass    
    [string]$FrequencyRampCombineRatio = 2     # Additional parameter to pass        
    #[string]$PulseWidthCombineRatio = 2     # Additional parameter to pass    
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
    python invert.py "$filenameOnly.speed.funscript"
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

# Get beta if available
$betaPath = [System.IO.Path]::ChangeExtension($Filename, ".beta.funscript")
if (Test-Path $betaPath) {
    # beta exists
    Copy-Item -Path $betaPath -Destination "$filenameOnly.beta.funscript"
}
else {
    Write-Output "beta not found"
}



# Define the full filenames with extensions
$File1 = "$Filename"
$File2 = "$filenameOnly.speed.funscript"

if (-Not (Test-Path $File2)) {
    # speed does NOT exist
    python convert-to-speed.py $File1 $File2 $SpeedWindowSizeInSeconds
    python invert.py $File2
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


$File1 = "$filenameOnly.alpha.funscript"
$File2 = "$filenameOnly.pulse_frequency-alphabased.funscript"

if (-Not (Test-Path $File2)) {
    # pulse_frequency does NOT exist
    python map-funscript.py $File1 $FreqMapMin $FreqMapMax $File2 
}
else {
    Write-Output "pulse_frequency already exists."
}


$File1 = "$filenameOnly.pulse_frequency-alphabased.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.pulse_frequency.funscript"

if (-Not (Test-Path $File3)) {
    # pulse_frequency does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File2 $File1 $File3 3
}
else {
    Write-Output "pulse_frequency already exists."
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


$File1 = "$filenameOnly.ramp.funscript"
if (Test-Path $File1) {
  $File2 = "$filenameOnly.ramp_inverted.funscript"
  if (-Not (Test-Path $File2)) {
      # ramp inverted does NOT exist
      # Call the Python script with the constructed arguments
      python invert.py $File1  
  }
  else {
      Write-Output "ramp_inverted already exists."
  }
}





$File1 = "$filenameOnly.ramp.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.volume-prostate.funscript"

if (-Not (Test-Path $File3)) {
    # volume does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File1 $File2 $File3 ($VolumeRampCombineRatio * 1.5) --rest_level=0.7
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
    python combine-funscripts.py $File1 $File2 $File3 $VolumeRampCombineRatio --rest_level=$rest_level
}
else {
    Write-Output "volume already exists."
}

$File1 = "$filenameOnly.volume.funscript"
$File2 = "$filenameOnly.volume-stereostim.funscript"

if (-Not (Test-Path $File2)) {
    # volume does NOT exist
    # Call the Python script with the constructed arguments
    python map-funscript.py $File3 0.50 1.00 $File2
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


$File1 = "$filenameOnly.beta.funscript"
$File2 = "$filenameOnly.beta-mirror-up.funscript"
if (-Not (Test-Path $File2)) {
    # beta-mirror-up does NOT exist
    python mirror-up.py $File1 0.5 $File2
}
else {
    Write-Output "beta-mirror-up already exists."
}


$File1 = "$filenameOnly.beta-mirror-up.funscript"
$File2 = "$filenameOnly.speed_inverted.funscript"
$File3 = "$filenameOnly.pulse_rise_time.funscript"
$File4 = "$filenameOnly.ramp_inverted.funscript"
if (-Not (Test-Path $File3)) {
    # pulse_rise_time does NOT exist
    python combine-funscripts.py $File1 $File2 $File3 2    
    python combine-funscripts.py $File4 $File3 $File3 2
    python map-funscript.py $File3 0.00 0.80 $File3
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


$File1 = "$filenameOnly.alpha_inverted.funscript"
$File2 = "$filenameOnly.pulse_width-alpha.funscript"

if (-Not (Test-Path $File2)) {
    # pulse_width-alpha does NOT exist
    python limit-funscript.py $File1 0.1 0.45 $File2
}
else {
    Write-Output "pulse_width-alpha already exists."
}

$File1 = "$filenameOnly.pulse_width-alpha.funscript"
$File2 = "$filenameOnly.speed.funscript"
$File3 = "$filenameOnly.pulse_width.funscript"

if (-Not (Test-Path $File3)) {
    # frequency does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File2 $File1 $File3 3
}
else {
    Write-Output "pulse_width already exists."
}

Copy-Item -Path "$filenameOnly.alpha.funscript"                 -Destination "./funscript-output/$filenameOnly.alpha.funscript"
Copy-Item -Path "$filenameOnly.alpha-prostate.funscript"        -Destination "./funscript-output/$filenameOnly.alpha-prostate.funscript"
Copy-Item -Path "$filenameOnly.beta.funscript"                  -Destination "./funscript-output/$filenameOnly.beta.funscript"
Copy-Item -Path "$filenameOnly.frequency.funscript"             -Destination "./funscript-output/$filenameOnly.frequency.funscript"
Copy-Item -Path "$filenameOnly.pulse_frequency.funscript"       -Destination "./funscript-output/$filenameOnly.pulse_frequency.funscript"
Copy-Item -Path "$filenameOnly.pulse_rise_time.funscript"       -Destination "./funscript-output/$filenameOnly.pulse_rise_time.funscript"
Copy-Item -Path "$filenameOnly.pulse_width.funscript"           -Destination "./funscript-output/$filenameOnly.pulse_width.funscript"
Copy-Item -Path "$filenameOnly.volume.funscript"                -Destination "./funscript-output/$filenameOnly.volume.funscript"
Copy-Item -Path "$filenameOnly.volume-prostate.funscript"       -Destination "./funscript-output/$filenameOnly.volume-prostate.funscript"
Copy-Item -Path "$filenameOnly.volume-stereostim.funscript"     -Destination "./funscript-output/$filenameOnly.volume-stereostim.funscript"


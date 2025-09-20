param (
    [string]$Filename,   # Base filename without extensions
    [string]$Parameter   # Additional parameter to pass
)

# Define the full filenames with extensions
$File1 = "$Filename.ramp.funscript"
$File2 = "$Filename.speed.funscript"
$File3 = "$Filename.volume.funscript"


# Call the Python script with the constructed arguments
python combine-funscripts.py $File1 $File2 $File3 $Parameter

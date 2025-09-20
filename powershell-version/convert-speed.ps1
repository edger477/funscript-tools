param (
    [string]$Filename,   # Base filename without extensions
    [string]$Parameter   # Additional parameter to pass
)

# Define the full filenames with extensions
$File1 = "$Filename.funscript"
$File2 = "$Filename.speed.funscript"


# Call the Python script with the constructed arguments
python convert-to-speed.py $File1 $File2 $Parameter

param (
    [string]$Filename                      #source funscript
)

$filenameOnly = [System.IO.Path]::GetFileNameWithoutExtension($Filename)
$directoryPath = Split-Path -Path $Filename


$File1 = "$directoryPath\$filenameOnly.e1.funscript"
$File2 = "$directoryPath\$filenameOnly.e2.funscript"
$File3 = "$directoryPath\$filenameOnly.e3.funscript"
$File4 = "$directoryPath\$filenameOnly.e4.funscript"
$File5 = "$directoryPath\$filenameOnly.alpha-prostate.funscript"

if (-Not (Test-Path $File4)) {
    # e4 does NOT exist
    # Call the Python script with the constructed arguments
    python combine-funscripts.py $File1 $File2 $File4 2    
    python combine-funscripts.py $File4 $File3 $File4 3
    #python limit-funscript.py $File4 0.0 0.99 $File4
    python map-funscript.py $File4 0.00 0.70 $File4
    if (Test-Path $File5) {
        python combine-funscripts.py $File4 $File5 $File4 4
    }
}
else {
    Write-Output "e4  already exists."
}


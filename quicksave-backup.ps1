# Configurable variables
$quicksavesToKeep = 5
$quicksaveInteralSeconds = 10
$numberOfRetries = 3
$secondsForRetry = 5

# Function to check if a path exists and return the valid path
function Get-ValidPath {
    param (
        [string]$steamPath,
        [string]$defaultPath,
        [string]$alternativePath
    )

    if (Test-Path $steamPath) {
        return $steamPath
    } elseif (Test-Path $defaultPath) {
        return $defaultPath
    } elseif (Test-Path $alternativePath) {
        return $alternativePath
    } else {
        do {
            $userPath = Read-Host "Enter the path to the Starfield Save folder"
            if (Test-Path $userPath) {
                return $userPath
            } else {
                Write-Host "Invalid path. Please try again."
            }
        } while ($true)
    }
}

# Function to get the Steam Cloud save path
function Get-SteamCloudPath {
    $steamUserdataPath = "C:\Program Files (x86)\Steam\userdata"
    if (Test-Path $steamUserdataPath) {
        $steamUserID = Get-ChildItem -Path $steamUserdataPath | Select-Object -First 1
        if ($steamUserID) {
            $steamCloudPath = Join-Path -Path $steamUserID.FullName -ChildPath "1716740\remote\Saves"
            if (Test-Path $steamCloudPath) {
                return $steamCloudPath
            }
        }
    }
    return $null
}

# Initialize variables
$currentUser = [System.Environment]::UserName
$defaultPath = "C:\Users\$currentUser\Documents\My Games\Starfield\Saves"
$alternativePath = "C:\Users\$currentUser\OneDrive\Documents\My Games\Starfield\Saves"
$steamCloudPath = Get-SteamCloudPath
$validPath = Get-ValidPath -steamPath $steamCloudPath -defaultPath $defaultPath -alternativePath $alternativePath

# Initialize counter for retries
$retryCounter = 0

# Function for error handling and retries
function Save-Quicksave {
    param (
        [ScriptBlock]$operation
    )

    do {
        try {
            $operation.Invoke()
            return $true
        } catch {
            $retryCounter++
            if ($retryCounter -ge $numberOfRetries) {
                Write-Host "Operation failed after " + $numberOfRetries + " attempts. Exiting."
                exit
            }
            Start-Sleep -Seconds $secondsForRetry
        }
    } while ($true)
}

# Main loop
while ($true) {
    # Check if Starfield is running
    $isRunning = Get-Process Starfield -ErrorAction SilentlyContinue
    if (-not $isRunning) {
        Write-Host "Starfield is no longer running. Exiting."
        exit
    }

    # Check for Quicksave files
    $quicksaveFile = Get-ChildItem -Path $validPath -Filter "Quicksave*.sfs" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($quicksaveFile) {
        $backupFiles = Get-ChildItem -Path $validPath -Filter "Quicksave*.backup" | Sort-Object LastWriteTime

        if ($backupFiles.Count -ge $quicksavesToKeep) {
            Save-Quicksave {
                Remove-Item $backupFiles[0].FullName
            }
        }

        $backupFileName = [System.IO.Path]::Combine($validPath, ($quicksaveFile.BaseName + ".backup"))

        if (-not (Test-Path $backupFileName)) {
            Save-Quicksave {
                Copy-Item $quicksaveFile.FullName $backupFileName
            }
            Write-Host "Backup made: $backupFileName"
        }
    }

    Start-Sleep -Seconds $quicksaveInteralSeconds
}

# Configurable variables
$quicksavesToKeep = 5
$quicksaveInteralSeconds = 10
$numberOfRetries = 3
$secondsForRetry = 5

<#
.SYNOPSIS
    Checks if a path exists and returns the first valid path.

.PARAMETER steamPath
    The path to the Steam Cloud save folder.

.PARAMETER defaultPath
    The default path to the Starfield save folder in Documents.

.PARAMETER alternativePath
    The alternative path to the Starfield save folder in OneDrive.

.RETURNS
    A string representing the first valid path.

.EXAMPLE
    $validPath = Get-ValidPath -steamPath $steamCloudPath -defaultPath $defaultPath -alternativePath $alternativePath
#>
function Get-ValidPath {
    param (
        [string]$steamPath,
        [string]$defaultPath,
        [string]$alternativePath
    )

    if (Test-Path $steamPath) {
        return $steamPath
    }
    elseif (Test-Path $defaultPath) {
        return $defaultPath
    }
    elseif (Test-Path $alternativePath) {
        return $alternativePath
    }
    else {
        do {
            $userPath = Read-Host "Enter the path to the Starfield Save folder"
            if (Test-Path $userPath) {
                return $userPath
            }
            else {
                Write-Host "Invalid path. Please try again."
            }
        } while ($true)
    }
}

<#
.SYNOPSIS
    Retrieves the Steam Cloud save path for Starfield.

.DESCRIPTION
    This function checks the Steam userdata directory for the first subfolder, which represents the Steam user ID.
    It constructs the path to the Starfield saves in the Steam Cloud and returns it if it exists.

.RETURNS
    A string representing the Steam Cloud save path, or $null if the path does not exist.

.EXAMPLE
    $steamCloudPath = Get-SteamCloudPath
#>
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

<#
.SYNOPSIS
    Executes an operation with retry logic.

.PARAMETER operation
    The script block containing the operation to be executed.

.DESCRIPTION
    This function attempts to execute the provided operation. If the operation fails, it retries up to a specified
    number of times, waiting for a specified number of seconds between retries.

.EXAMPLE
    Save-QuicksaveFile {
        Copy-Item $quicksaveFile.FullName $backupFileName
    }
#>
function Save-Quicksave {
    param (
        [ScriptBlock]$operation
    )

    do {
        try {
            $operation.Invoke() | Out-Null
            return $true
        }
        catch {
            $retryCounter++
            if ($retryCounter -ge $numberOfRetries) {
                Write-Host "Operation failed after " + $numberOfRetries + " attempts. Exiting."
                exit
            }
            Start-Sleep -Seconds $secondsForRetry
        }
    } while ($true)
}

# Main loop to monitor Starfield quicksaves and create backups
while ($true) {
    # Check if Starfield is running by looking for any process with "Starfield" in its name
    $isRunning = Get-Process | Where-Object { $_.Name -like "*Starfield*" }
    if (-not $isRunning) {
        Write-Host "Starfield is no longer running. Exiting."
        exit
    }

    # Check for quicksave files
    $quicksaveFile = Get-ChildItem -Path $validPath -Filter "Quicksave*.sfs" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($quicksaveFile) {
        $backupFiles = Get-ChildItem -Path $validPath -Filter "Quicksave*.backup" | Sort-Object LastWriteTime

        # Remove oldest backup if limit is reached
        if ($backupFiles.Count -ge $quicksavesToKeep) {
            Save-QuicksaveFile {
                Remove-Item $backupFiles[0].FullName
            }
        }

        $backupFileName = [System.IO.Path]::Combine($validPath, ($quicksaveFile.BaseName + ".backup"))

        # Create a backup if it doesn't already exist
        if (-not (Test-Path $backupFileName)) {
            Save-QuicksaveFile {
                Copy-Item $quicksaveFile.FullName $backupFileName
            }
            Write-Host "Backup made: $backupFileName"
        }
    }

    Start-Sleep -Seconds $quicksaveInteralSeconds
}

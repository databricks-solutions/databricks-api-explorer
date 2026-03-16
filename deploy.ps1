$AppName = "databricks-api-explorer"
$ConfigFile = Join-Path $env:USERPROFILE ".databrickscfg"

if (-not (Test-Path $ConfigFile)) {
    Write-Host "Error: $ConfigFile not found" -ForegroundColor Red
    exit 1
}

# Parse profile names and hosts from .databrickscfg
$profiles = @()
$hosts = @()
$currentProfile = $null

foreach ($line in Get-Content $ConfigFile) {
    if ($line -match '^\[(.+)\]$') {
        $currentProfile = $Matches[1]
    }
    elseif ($line -match '^host\s*=\s*(.+)$') {
        $host = $Matches[1].Trim().TrimEnd('/')
        $profiles += $currentProfile
        $hosts += $host
    }
}

if ($profiles.Count -eq 0) {
    Write-Host "Error: No profiles found in $ConfigFile" -ForegroundColor Red
    exit 1
}

# Interactive selector
$selected = 0
$total = $profiles.Count

function Draw-Menu {
    param([bool]$Redraw = $false)

    if ($Redraw) {
        [Console]::SetCursorPosition(0, [Console]::CursorTop - $total)
    }

    for ($i = 0; $i -lt $total; $i++) {
        $profilePad = $profiles[$i].PadRight(35)
        if ($i -eq $selected) {
            Write-Host "  > $profilePad $($hosts[$i])" -ForegroundColor Cyan
        }
        else {
            Write-Host "    $profilePad " -NoNewline
            Write-Host $hosts[$i] -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
Write-Host "  Select a workspace to deploy ${AppName} to:"
Write-Host "  (Up/Down to move, Enter to select, Q to quit)"
Write-Host ""

[Console]::CursorVisible = $false
try {
    Draw-Menu

    while ($true) {
        $key = [Console]::ReadKey($true)

        switch ($key.Key) {
            'UpArrow' {
                if ($selected -gt 0) { $selected-- }
            }
            'DownArrow' {
                if ($selected -lt $total - 1) { $selected++ }
            }
            'Enter' {
                break
            }
            'Q' {
                Write-Host ""
                Write-Host "  Cancelled."
                exit 0
            }
            default { continue }
        }

        if ($key.Key -eq 'Enter') { break }

        Draw-Menu -Redraw $true
    }
}
finally {
    [Console]::CursorVisible = $true
}

$profile = $profiles[$selected]
$host = $hosts[$selected]

Write-Host ""
Write-Host "  Deploying ${AppName} to:"
Write-Host "    Profile:   $profile"
Write-Host "    Workspace: $host"
Write-Host ""

# Deploy
databricks apps deploy $AppName --source-code-path . --profile $profile

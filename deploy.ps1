$AppName = "api_explorer"
$DeployedAppName = "databricks-api-explorer"
$Screenshot = Join-Path $PSScriptRoot "assets" "Screenshot Databricks App.png"
$OboScopes = '["offline_access","email","iam.current-user:read","openid","iam.access-control:read","profile","all-apis"]'
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

# Deploy via asset bundle
Write-Host "  Running: databricks bundle deploy --profile `"$profile`""
Write-Host ""
databricks bundle deploy --profile $profile

Write-Host ""
Write-Host "  Running: databricks bundle run $AppName --profile `"$profile`""
Write-Host ""
databricks bundle run $AppName --profile $profile

# Get app metadata
$appData = $null
$integrationId = $null
$spId = $null
try {
    $appData = databricks apps get $DeployedAppName --profile $profile -o json 2>$null | ConvertFrom-Json
    $integrationId = $appData.oauth2_app_integration_id
    $spId = $appData.service_principal_id
} catch {}

# Upload app thumbnail
if (Test-Path $Screenshot) {
    Write-Host ""
    Write-Host "  Uploading app thumbnail..."
    try {
        $tokenJson = databricks auth token --profile $profile 2>$null | ConvertFrom-Json
        $token = $tokenJson.access_token
        $wsHost = (python3 -c "
from databricks.sdk.core import Config
c = Config(profile='$profile')
print((c.host or '').rstrip('/'))
" 2>$null).Trim()
        if ($token -and $wsHost) {
            $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($Screenshot))
            $body = "{`"encoded_thumbnail`": `"$b64`"}"
            Invoke-RestMethod -Uri "$wsHost/api/2.0/apps/$DeployedAppName/thumbnail" `
                -Method Post -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } `
                -Body $body 2>$null | Out-Null
            Write-Host "  Thumbnail uploaded." -ForegroundColor Green
        } else {
            Write-Host "  Warning: Could not upload thumbnail (missing token or host)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Warning: Could not upload thumbnail." -ForegroundColor Yellow
    }
}

# Configure OBO scopes (requires an account-level profile)
Write-Host ""
Write-Host "  Configuring OBO user authorization scopes..."

if (-not $integrationId) {
    Write-Host "  Warning: Could not retrieve app integration ID. OBO scopes not configured." -ForegroundColor Yellow
    Write-Host "  Configure them manually in the Databricks Apps UI -> Configure -> Add scope."
}
else {
    # Find an account-level profile (host contains 'accounts.')
    $accountProfile = $null
    $currentProf = $null
    foreach ($line in Get-Content $ConfigFile) {
        if ($line -match '^\[(.+)\]$') {
            $currentProf = $Matches[1]
        }
        elseif ($line -match '^host\s*=\s*(.+)$') {
            $h = $Matches[1].Trim()
            if ($h -like "*accounts.*") {
                $accountProfile = $currentProf
                break
            }
        }
    }

    if (-not $accountProfile) {
        Write-Host "  Warning: No account-level profile found in ~/.databrickscfg." -ForegroundColor Yellow
        Write-Host "  OBO scopes not configured. Add them in the Databricks Apps UI -> Configure -> Add scope."
    }
    else {
        Write-Host "  Using account profile: $accountProfile"
        Write-Host "  Integration ID: $integrationId"

        try {
            $integJson = databricks account custom-app-integration get $integrationId --profile $accountProfile -o json 2>$null | ConvertFrom-Json
            $redirectUrls = ($integJson.redirect_urls | ConvertTo-Json -Compress)
        } catch {
            $redirectUrls = "[]"
        }

        $updateJson = "{`"scopes`": $OboScopes, `"redirect_urls`": $redirectUrls}"
        try {
            databricks account custom-app-integration update $integrationId --profile $accountProfile --json $updateJson 2>$null
            Write-Host "  OBO scopes configured successfully: all-apis enabled." -ForegroundColor Green
        } catch {
            Write-Host "  Warning: Could not update OBO scopes. Configure them manually in the Databricks Apps UI." -ForegroundColor Yellow
        }
    }
}

# Add Service Principal to admins group
if ($spId) {
    $spInAdmins = $false
    try {
        $adminsJson = databricks groups get admins --profile $profile -o json 2>$null | ConvertFrom-Json
        $spInAdmins = ($adminsJson.members | Where-Object { $_.value -eq "$spId" }).Count -gt 0
    } catch {}

    if ($spInAdmins) {
        Write-Host ""
        Write-Host "  App Service Principal (ID: $spId) is already in the admins group."
    }
    else {
        Write-Host ""
        Write-Host "  The app's Service Principal (ID: $spId) is NOT in the admins group."
        Write-Host "  Adding it to admins allows the SP to access all workspace objects."
        $addToAdmins = Read-Host "  Add Service Principal to admins group? [y/N]"

        if ($addToAdmins -match '^[Yy]$') {
            $patchJson = '{"Operations": [{"op": "add", "value": {"members": [{"value": "' + $spId + '"}]}}], "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]}'
            try {
                databricks groups patch admins --profile $profile --json $patchJson 2>$null
                Write-Host "  Service Principal added to admins group." -ForegroundColor Green
            } catch {
                Write-Host "  Warning: Could not add SP to admins group. Add it manually via Settings -> Identity and access -> Groups -> admins." -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "  Skipped. The SP may not be able to access all workspace objects."
        }
    }
}

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
Write-Host ""
Write-Host "  Fetching app metadata..."
$appData = $null
$integrationId = $null
$spId = $null
$spName = $null
try {
    $appData = databricks apps get $DeployedAppName --profile $profile -o json 2>$null | ConvertFrom-Json
    $integrationId = $appData.oauth2_app_integration_id
    $spId = $appData.service_principal_id
    $spName = $appData.service_principal_name
} catch {
    Write-Host "  Warning: Could not fetch app metadata." -ForegroundColor Yellow
}
Write-Host "  App integration ID: $(if ($integrationId) { $integrationId } else { 'not found' })"
Write-Host "  Service Principal:  $(if ($spName) { $spName } else { 'unknown' }) (ID: $(if ($spId) { $spId } else { 'not found' }))"

# Get auth token + workspace host for API calls
$token = $null
$wsHost = $null
try {
    $tokenJson = databricks auth token --profile $profile 2>$null | ConvertFrom-Json
    $token = $tokenJson.access_token
    $wsHost = (python3 -c "
from databricks.sdk.core import Config
c = Config(profile='$profile')
print((c.host or '').rstrip('/'))
" 2>$null).Trim()
} catch {}

# Upload app thumbnail
if (Test-Path $Screenshot) {
    Write-Host ""
    Write-Host "  Uploading app thumbnail..."
    if ($token -and $wsHost) {
        try {
            $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($Screenshot))
            $body = "{`"encoded_thumbnail`": `"$b64`"}"
            Invoke-RestMethod -Uri "$wsHost/api/2.0/apps/$DeployedAppName/thumbnail" `
                -Method Post -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } `
                -Body $body 2>$null | Out-Null
            Write-Host "  Thumbnail uploaded." -ForegroundColor Green
        } catch {
            Write-Host "  Warning: Could not upload thumbnail." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Warning: Could not upload thumbnail (missing token or host)." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "  Skipping thumbnail upload ($Screenshot not found)."
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
        Write-Host "  Updating integration $integrationId with all-apis scope..."

        try {
            $integJson = databricks account custom-app-integration get $integrationId --profile $accountProfile -o json 2>$null | ConvertFrom-Json
            $redirectUrls = ($integJson.redirect_urls | ConvertTo-Json -Compress)
        } catch {
            $redirectUrls = "[]"
        }

        $updateJson = "{`"scopes`": $OboScopes, `"redirect_urls`": $redirectUrls}"
        try {
            databricks account custom-app-integration update $integrationId --profile $accountProfile --json $updateJson 2>$null
            Write-Host "  OBO scopes configured successfully." -ForegroundColor Green
        } catch {
            Write-Host "  Warning: Could not update OBO scopes. Configure them manually in the Databricks Apps UI." -ForegroundColor Yellow
        }
    }
}

# Add Service Principal to admins group
Write-Host ""
Write-Host "  Checking Service Principal admin group membership..."

if (-not $spId) {
    Write-Host "  Warning: No Service Principal ID found - skipping admins group check." -ForegroundColor Yellow
}
elseif (-not $token -or -not $wsHost) {
    Write-Host "  Warning: No auth token or host - skipping admins group check." -ForegroundColor Yellow
}
else {
    # Use SCIM API to find admins group and check membership
    try {
        $adminsScim = Invoke-RestMethod -Uri "$wsHost/api/2.0/preview/scim/v2/Groups?filter=displayName+eq+%22admins%22" `
            -Headers @{ Authorization = "Bearer $token" } 2>$null
        $adminsGroup = $adminsScim.Resources | Select-Object -First 1
        $adminsGroupId = $adminsGroup.id
        $spInAdmins = ($adminsGroup.members | Where-Object { "$($_.value)" -eq "$spId" }).Count -gt 0
    } catch {
        $adminsGroupId = $null
        $spInAdmins = $false
    }

    if (-not $adminsGroupId) {
        Write-Host "  Warning: Could not find admins group via SCIM API." -ForegroundColor Yellow
    }
    elseif ($spInAdmins) {
        Write-Host "  $spName (ID: $spId) is already in the admins group."
    }
    else {
        Write-Host "  $spName (ID: $spId) is NOT in the admins group."
        Write-Host "  Adding it to admins allows the SP to access all workspace objects."
        $addToAdmins = Read-Host "  Add Service Principal to admins group? [y/N]"

        if ($addToAdmins -match '^[Yy]$') {
            Write-Host "  Adding SP to admins group (SCIM group ID: $adminsGroupId)..."
            try {
                $patchBody = "{`"Operations`": [{`"op`": `"add`", `"path`": `"members`", `"value`": [{`"value`": `"$spId`"}]}], `"schemas`": [`"urn:ietf:params:scim:api:messages:2.0:PatchOp`"]}"
                Invoke-RestMethod -Uri "$wsHost/api/2.0/preview/scim/v2/Groups/$adminsGroupId" `
                    -Method Patch -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/scim+json" } `
                    -Body $patchBody 2>$null | Out-Null
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

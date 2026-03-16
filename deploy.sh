#!/usr/bin/env bash
set -euo pipefail

APP_NAME="api_explorer"
DEPLOYED_APP_NAME="databricks-api-explorer"
SCREENSHOT="$(cd "$(dirname "$0")" && pwd)/assets/Screenshot Databricks App.png"
OBO_SCOPES='["offline_access","email","iam.current-user:read","openid","iam.access-control:read","profile","all-apis"]'
CONFIG_FILE="${HOME}/.databrickscfg"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Error: $CONFIG_FILE not found"
  exit 1
fi

# Parse profile names and hosts from .databrickscfg
profiles=()
hosts=()
while IFS= read -r line; do
  if [[ "$line" =~ ^\[(.+)\]$ ]]; then
    current_profile="${BASH_REMATCH[1]}"
  elif [[ "$line" =~ ^host[[:space:]]*=[[:space:]]*(.+)$ ]]; then
    host="${BASH_REMATCH[1]}"
    host="${host%/}"  # strip trailing slash
    profiles+=("$current_profile")
    hosts+=("$host")
  fi
done < "$CONFIG_FILE"

if [[ ${#profiles[@]} -eq 0 ]]; then
  echo "Error: No profiles found in $CONFIG_FILE"
  exit 1
fi

# Interactive selector
selected=0
total=${#profiles[@]}

draw_menu() {
  # Move cursor up to redraw (skip on first draw)
  if [[ ${1:-0} -eq 1 ]]; then
    printf "\033[%dA" "$total"
  fi

  for i in $(seq 0 $((total - 1))); do
    if [[ $i -eq $selected ]]; then
      printf "\033[1;36m  ▸ %-35s %s\033[0m\n" "${profiles[$i]}" "${hosts[$i]}"
    else
      printf "    %-35s \033[2m%s\033[0m\n" "${profiles[$i]}" "${hosts[$i]}"
    fi
  done
}

echo ""
echo "  Select a workspace to deploy ${APP_NAME} to:"
echo "  (↑/↓ to move, Enter to select, q to quit)"
echo ""

# Hide cursor
printf "\033[?25l"
trap 'printf "\033[?25h"' EXIT

draw_menu 0

while true; do
  # Read a single keypress
  IFS= read -rsn1 key

  if [[ "$key" == $'\x1b' ]]; then
    read -rsn2 rest
    key+="$rest"
  fi

  case "$key" in
    $'\x1b[A') # Up arrow
      ((selected > 0)) && ((selected--))
      ;;
    $'\x1b[B') # Down arrow
      ((selected < total - 1)) && ((selected++))
      ;;
    '') # Enter
      break
      ;;
    q|Q)
      echo ""
      echo "  Cancelled."
      exit 0
      ;;
    *)
      continue
      ;;
  esac

  draw_menu 1
done

# Restore cursor
printf "\033[?25h"
trap - EXIT

profile="${profiles[$selected]}"
host="${hosts[$selected]}"

echo ""
echo "  Deploying ${APP_NAME} to:"
echo "    Profile:   ${profile}"
echo "    Workspace: ${host}"
echo ""

# Deploy via asset bundle
echo "  Running: databricks bundle deploy --profile \"${profile}\""
echo ""
databricks bundle deploy --profile "$profile"

echo ""
echo "  Running: databricks bundle run ${APP_NAME} --profile \"${profile}\""
echo ""
databricks bundle run "$APP_NAME" --profile "$profile"

# ── Get app metadata ─────────────────────────────────────────────────
app_json=$(databricks apps get "$DEPLOYED_APP_NAME" --profile "$profile" -o json 2>/dev/null || echo "{}")
integration_id=$(echo "$app_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('oauth2_app_integration_id',''))" 2>/dev/null)
sp_id=$(echo "$app_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('service_principal_id',''))" 2>/dev/null)

# ── Upload app thumbnail ─────────────────────────────────────────────
if [[ -f "$SCREENSHOT" ]]; then
  echo ""
  echo "  Uploading app thumbnail..."
  _token=$(databricks auth token --profile "$profile" 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
  _ws_host=$(echo "$app_json" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('url',''); print(u.split('.')[0].replace('https://','').rsplit('-',1)[0] if u else '')" 2>/dev/null)
  # Derive workspace host from the profile
  _ws_host=$(python3 -c "
from databricks.sdk.core import Config
c = Config(profile='${profile}')
print((c.host or '').rstrip('/'))
" 2>/dev/null)
  if [[ -n "$_token" && -n "$_ws_host" ]]; then
    _b64=$(base64 -i "$SCREENSHOT")
    _resp=$(curl -s -X POST "${_ws_host}/api/2.0/apps/${DEPLOYED_APP_NAME}/thumbnail" \
      -H "Authorization: Bearer ${_token}" \
      -H "Content-Type: application/json" \
      -d "{\"encoded_thumbnail\": \"${_b64}\"}" 2>&1)
    echo "  Thumbnail uploaded."
  else
    echo "  Warning: Could not upload thumbnail (missing token or host)."
  fi
fi

# ── Configure OBO scopes (requires an account-level profile) ──────────
echo ""
echo "  Configuring OBO user authorization scopes..."

if [[ -z "$integration_id" ]]; then
  echo "  Warning: Could not retrieve app integration ID. OBO scopes not configured."
  echo "  You can configure them manually in the Databricks Apps UI → Configure → Add scope."
else
  # Find an account-level profile (host contains 'accounts.')
  account_profile=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^\[(.+)\]$ ]]; then
      _prof="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^host[[:space:]]*=[[:space:]]*(.+)$ ]]; then
      _host="${BASH_REMATCH[1]}"
      if [[ "$_host" == *"accounts."* ]]; then
        account_profile="$_prof"
        break
      fi
    fi
  done < "$CONFIG_FILE"

  if [[ -z "$account_profile" ]]; then
    echo "  Warning: No account-level profile found in ~/.databrickscfg."
    echo "  OBO scopes not configured. Add them in the Databricks Apps UI → Configure → Add scope."
  else
    echo "  Using account profile: ${account_profile}"
    echo "  Integration ID: ${integration_id}"

    redirect_urls=$(databricks account custom-app-integration get "$integration_id" \
      --profile "$account_profile" -o json 2>/dev/null \
      | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('redirect_urls',[])))" 2>/dev/null)

    databricks account custom-app-integration update "$integration_id" \
      --profile "$account_profile" \
      --json "{\"scopes\": ${OBO_SCOPES}, \"redirect_urls\": ${redirect_urls:-"[]"}}" 2>/dev/null \
      && echo "  OBO scopes configured successfully: all-apis enabled." \
      || echo "  Warning: Could not update OBO scopes. Configure them manually in the Databricks Apps UI."
  fi
fi

# ── Add Service Principal to admins group ─────────────────────────────
if [[ -n "$sp_id" ]]; then
  # Check if the SP is already in the admins group
  admins_json=$(databricks groups get admins --profile "$profile" -o json 2>/dev/null || echo "{}")
  sp_in_admins=$(echo "$admins_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
members = data.get('members', [])
sp_id = '${sp_id}'
print('yes' if any(str(m.get('value')) == sp_id for m in members) else 'no')
" 2>/dev/null)

  if [[ "$sp_in_admins" == "yes" ]]; then
    echo ""
    echo "  App Service Principal (ID: ${sp_id}) is already in the admins group."
  else
    echo ""
    echo "  The app's Service Principal (ID: ${sp_id}) is NOT in the admins group."
    echo "  Adding it to admins allows the SP to access all workspace objects."
    printf "  Add Service Principal to admins group? [y/N] "
    read -r add_to_admins

    if [[ "$add_to_admins" =~ ^[Yy]$ ]]; then
      databricks groups patch admins --profile "$profile" \
        --json "{\"Operations\": [{\"op\": \"add\", \"value\": {\"members\": [{\"value\": \"${sp_id}\"}]}}], \"schemas\": [\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"]}" 2>/dev/null \
        && echo "  Service Principal added to admins group." \
        || echo "  Warning: Could not add SP to admins group. Add it manually via Settings → Identity and access → Groups → admins."
    else
      echo "  Skipped. The SP may not be able to access all workspace objects."
    fi
  fi
fi

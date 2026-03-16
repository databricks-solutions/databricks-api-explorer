#!/usr/bin/env bash
set -euo pipefail

APP_NAME="databricks-api-explorer"
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

# Deploy
databricks apps deploy "$APP_NAME" \
  --source-code-path . \
  --profile "$profile"

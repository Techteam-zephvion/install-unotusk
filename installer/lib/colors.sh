#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Colors and Indicators Library
# ==============================================================================

# Determine if output is a terminal
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  RESET='\033[0m'
else
  RED=''
  GREEN=''
  YELLOW=''
  CYAN=''
  BOLD=''
  RESET=''
fi

# Print functions with indicators
# Usage: log_success "Message"
log_info()    { echo -e "  ${CYAN}→${RESET} $*"; }
log_success() { echo -e "  ${GREEN}✔${RESET} $*"; }
log_warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; }
log_error()   { echo -e "  ${RED}✘${RESET} $*"; }
log_header()  { echo -e "\n${BOLD}$*${RESET}"; }
log_title()   {
  local text="$1"
  local width=42
  local padding=$(( (width - ${#text}) / 2 ))
  local pad_str=$(printf '%*s' $padding '')
  echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
  printf "${BOLD}║%s%-*s║\n${RESET}" "$pad_str" $(( width - padding )) "$text"
  echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
}

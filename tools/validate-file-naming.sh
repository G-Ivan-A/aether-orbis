#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

failures=0

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  failures=$((failures + 1))
}

is_exception() {
  local basename="$1"

  case "$basename" in
    README.md | \
    CHANGELOG.md | \
    CONTRIBUTING.md | \
    CODE_OF_CONDUCT.md | \
    LICENSE | \
    LICENSE.md | \
    AI_GOVERNANCE.md | \
    *-registry.md | \
    *-index.md | \
    *-Index.md)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_daily_chronological_name() {
  local basename="$1"

  [[ "$basename" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*(\.[a-z]{2}(-[a-z]{2})*)?\.md$ ]]
}

is_monthly_chronological_name() {
  local basename="$1"

  [[ "$basename" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}- ]] && return 1
  [[ "$basename" =~ ^([0-9]{4}|[0-9]{4}-[0-9]{2})-[a-z0-9]+(-[a-z0-9]+)*(\.[a-z]{2}(-[a-z]{2})*)?\.md$ ]]
}

is_adr_chronological_name() {
  local basename="$1"

  [[ "$basename" =~ ^[0-9]{4}-[0-9]{2}-adr-[0-9]{3}-[a-z0-9]+(-[a-z0-9]+)*(\.[a-z]{2}(-[a-z]{2})*)?\.md$ ]]
}

validate_file() {
  local file="$1"
  local predicate="$2"
  local expected_format="$3"
  local basename="${file##*/}"

  if is_exception "$basename"; then
    return
  fi

  if ! "$predicate" "$basename"; then
    fail "chronological markdown file must use $expected_format: $file"
  fi
}

validate_tree() {
  local dir="$1"
  local predicate="$2"
  local expected_format="$3"

  [[ -d "$dir" ]] || return 0

  while IFS= read -r file; do
    validate_file "$file" "$predicate" "$expected_format"
  done < <(find "$dir" -type f -name '*.md' | sort)
}

validate_tree "docs/analysis" "is_daily_chronological_name" "YYYY-MM-DD-name.md"
validate_tree "docs/rfc" "is_monthly_chronological_name" "YYYY-MM-name.md or YYYY-name.md"
validate_tree "docs/adr" "is_adr_chronological_name" "YYYY-MM-adr-NNN-name.md"

if (( failures > 0 )); then
  printf 'File naming validation failed with %d error(s).\n' "$failures" >&2
  exit 1
fi

printf 'File naming validation passed.\n'

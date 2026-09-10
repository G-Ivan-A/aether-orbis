#!/usr/bin/env bash
# Проверка frontmatter-контракта Хаба для активных markdown-артефактов AetherOrbis.
# Требования: status, version, updated, temperature; owner для governance-артефактов;
# decision-type для ADR; поле ai-generated запрещено.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

failures=0
fail() { printf 'ERROR: %s\n' "$1" >&2; failures=$((failures + 1)); }

KNOWLEDGE_STATUSES="draft reviewed canonical superseded"
GOVERNANCE_STATUSES="draft proposed accepted rejected deprecated superseded"

has_field() { grep -qE "^$2:" "$1"; }
field_value() { sed -n "s/^$2:[[:space:]]*//p" "$1" | head -1; }

in_list() {
  local needle="$1"; shift
  for item in $*; do [[ "$item" == "$needle" ]] && return 0; done
  return 1
}

check_file() {
  local file="$1" kind="$2" statuses="$3"

  head -1 "$file" | grep -qx -- '---' || { fail "missing frontmatter: $file"; return; }

  for field in status version updated temperature; do
    has_field "$file" "$field" || fail "missing frontmatter field '$field': $file"
  done

  if grep -qE '^ai-generated:' "$file"; then
    fail "forbidden frontmatter field 'ai-generated': $file"
  fi

  local status
  status="$(field_value "$file" status)"
  in_list "$status" "$statuses" || fail "invalid status '$status' for $kind artifact: $file"

  if [[ "$kind" == "governance" ]]; then
    has_field "$file" owner || fail "missing frontmatter field 'owner': $file"
  fi

  if [[ "$file" == docs/adr/*adr-* ]]; then
    has_field "$file" decision-type || fail "missing frontmatter field 'decision-type': $file"
  fi
}

while IFS= read -r file; do
  check_file "$file" governance "$GOVERNANCE_STATUSES"
done < <(find docs/adr docs/standards -type f -name '*.md' ! -name 'README.md' | sort)

while IFS= read -r file; do
  basename="${file##*/}"
  adr_id="$(printf '%s\n' "$basename" | sed -E 's/^[0-9]{4}-[0-9]{2}-adr-([0-9]{3})-.*/ADR-\1/')"
  adr_status="$(field_value "$file" status)"
  registry_entry="$(grep -E "^\\| $adr_id \\|" docs/adr/README.md || true)"
  if [[ -z "$registry_entry" ]]; then
    fail "ADR registry is missing $adr_id from $file"
  elif ! grep -qE "\\|[[:space:]]*$adr_status[[:space:]]*\\|" <<<"$registry_entry"; then
    fail "ADR registry status for $adr_id does not match '$adr_status' in $file"
  fi
done < <(find docs/adr -maxdepth 1 -type f -name '*-adr-*.md' | sort)

for file in docs/README.md docs/vision.md docs/concept.md docs/architecture.md \
            docs/roadmap.md docs/adr/README.md PRODUCT_VISION.md GOVERNANCE.md; do
  [[ -f "$file" ]] || continue
  if [[ "$file" == GOVERNANCE.md ]]; then
    check_file "$file" governance "$GOVERNANCE_STATUSES"
  else
    check_file "$file" knowledge "$KNOWLEDGE_STATUSES"
  fi
done

if (( failures > 0 )); then
  printf 'Frontmatter validation failed with %d error(s).\n' "$failures" >&2
  exit 1
fi

printf 'Frontmatter validation passed.\n'

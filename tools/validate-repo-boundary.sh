#!/usr/bin/env bash
# Проверка границы «репозиторий / runtime»: runtime-данные и секреты не должны
# попадать в git. См. docs/adr/2026-08-adr-003-infrastructure.md.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

failures=0
fail() { printf 'ERROR: %s\n' "$1" >&2; failures=$((failures + 1)); }

FORBIDDEN_PATHS='^(data|storage|raw|sources|runs|artifacts|telemetry|logs|secrets|crawl_cache|extracted)/'
FORBIDDEN_FILES='\.(db|sqlite|sqlite3|duckdb|log|pem|key)$|(^|/)\.env($|\.)'

while IFS= read -r file; do
  [[ "$file" =~ $FORBIDDEN_PATHS ]] && fail "runtime data must not be tracked in git: $file"
  [[ "$file" =~ $FORBIDDEN_FILES ]] && fail "runtime or secret file must not be tracked in git: $file"
done < <(git ls-files)

for entry in ".env" "data/" "raw/" "runs/" "telemetry/" "logs/"; do
  grep -qF -- "$entry" .gitignore || fail ".gitignore must ignore: $entry"
done

if (( failures > 0 )); then
  printf 'Repository boundary validation failed with %d error(s).\n' "$failures" >&2
  exit 1
fi

printf 'Repository boundary validation passed.\n'

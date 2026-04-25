#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-app/db/migrations}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --database-url)
      DATABASE_URL="${2:-}"
      shift 2
      ;;
    --migrations-dir)
      MIGRATIONS_DIR="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -f ".env" ]]; then
  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "${line:0:1}" == "#" || "$line" != *=* ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    val="${val%\"}"
    val="${val#\"}"
    export "$key=$val"
  done < ".env"
fi

if [[ -z "$DATABASE_URL" ]]; then
  DATABASE_URL="${SUPABASE_DB_URL:-}"
fi

if [[ -z "$DATABASE_URL" ]]; then
  echo "Missing database URL. Pass --database-url or set SUPABASE_DB_URL in .env." >&2
  exit 1
fi

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
  echo "Migrations directory not found: $MIGRATIONS_DIR" >&2
  exit 1
fi

mapfile -t files < <(find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name '*.sql' | sort)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No SQL migrations found in $MIGRATIONS_DIR" >&2
  exit 1
fi

echo "Applying migrations to Supabase..."
for file in "${files[@]}"; do
  echo " - $(basename "$file")"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
done

echo "Supabase migrations complete."


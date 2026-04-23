# Backup Postgres from Docker and Restore to Supabase

## 1) Create a backup from your Docker Postgres

Replace these values first:

- `postgres_container_name`
- `your_db`
- `your_db_user`

```bash
CONTAINER=postgres_container_name
DB_NAME=your_db
DB_USER=your_db_user

# Create dump inside container (custom format)
docker exec -t $CONTAINER pg_dump \
  -U $DB_USER \
  -d $DB_NAME \
  -n public \
  --no-owner \
  --no-privileges \
  -F c \
  -f /tmp/db.dump

# Copy dump to your local machine
docker cp ${CONTAINER}:/tmp/db.dump ./db.dump
```

## 2) Get Supabase database password

In Supabase Dashboard:

1. Open your project.
2. Go to `Project Settings` -> `Database`.
3. Copy/reset the database password for the `postgres` user.

## 3) Restore into Supabase

Use your project ref (`phelmzejdigexrqqiwaw`) and region host shown in Dashboard.
Use the Session Pooler connection (port `5432`).

```bash
export SUPABASE_DB_URL="postgres://postgres.phelmzejdigexrqqiwaw:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres"

pg_restore \
  --dbname="$SUPABASE_DB_URL" \
  --no-owner \
  --no-privileges \
  --verbose \
  ./db.dump
```

## 4) Verify tables were restored

```bash
psql "$SUPABASE_DB_URL" -c "\dt public.*"
```

## Quick troubleshooting

- If restore fails on permissions: keep `--no-owner --no-privileges`.
- If restore fails on schemas: dump only `public` (`-n public`).
- If extension errors appear: enable matching extensions in Supabase first.

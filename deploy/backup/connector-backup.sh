#!/usr/bin/env bash
# Consistent backup of the SQLite database (and the env file) for the docker compose deployment.
#
# Uses SQLite's online backup API inside the running container, so it is safe while the
# service is up. Verifies each snapshot, keeps KEEP_DAYS of history (never fewer than
# KEEP_MIN snapshots), and backs up the env file (it holds ENCRYPTION_KEY) only when it changes.
#
# Typical use (root cron, daily):
#   15 3 * * * COMPOSE_DIR=/home/ubuntu/open-agent-connector /home/ubuntu/open-agent-connector/deploy/backup/connector-backup.sh >> /var/log/connector-backup.log 2>&1
#
# On-box snapshots protect against corruption and bad migrations. They do NOT protect against
# losing the machine: copy BACKUP_DIR off the host as well.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/open-agent-connector}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/connector}"
KEEP_DAYS="${KEEP_DAYS:-14}"
KEEP_MIN="${KEEP_MIN:-3}"
ENV_FILE="${ENV_FILE:-.env.prod}"
DB_PATH_IN_CONTAINER="${DB_PATH_IN_CONTAINER:-/app/data/connector.db}"
SERVICE="${SERVICE:-server}"

umask 077
cd "$COMPOSE_DIR"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
compose=(docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$ENV_FILE")
tmp_in_container="/tmp/connector-backup-$ts.db"
out="$BACKUP_DIR/connector-$ts.db"

echo "[$ts] snapshot start"
"${compose[@]}" exec -T "$SERVICE" python - "$DB_PATH_IN_CONTAINER" "$tmp_in_container" <<'PY'
import sqlite3, sys
src = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
PY
container_id="$("${compose[@]}" ps -q "$SERVICE")"
docker cp "$container_id:$tmp_in_container" "$out"
"${compose[@]}" exec -T "$SERVICE" rm -f "$tmp_in_container"

# Verify the copy before trusting it
python3 - "$out" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
result = db.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit(f"integrity_check failed: {result}")
tables = [r[0] for r in db.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
counts = {t: db.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}
print("verified:", ", ".join(f"{t}={n}" for t, n in sorted(counts.items()) if n) or "empty database")
PY
gzip -f "$out"
echo "[$ts] wrote $(basename "$out").gz ($(du -h "$out.gz" | cut -f1))"

# Env file (contains the encryption key): copy only when it changed
if [ -f "$ENV_FILE" ]; then
  latest_env="$(ls -1t "$BACKUP_DIR"/env.* 2>/dev/null | head -n1 || true)"
  if [ -z "$latest_env" ] || ! cmp -s "$ENV_FILE" "$latest_env"; then
    cp "$ENV_FILE" "$BACKUP_DIR/env.$ts"
    echo "[$ts] env file changed, saved env.$ts"
  fi
fi

# Rotation: drop snapshots older than KEEP_DAYS, but always keep the newest KEEP_MIN
mapfile -t snaps < <(ls -1t "$BACKUP_DIR"/connector-*.db.gz 2>/dev/null)
if [ "${#snaps[@]}" -gt "$KEEP_MIN" ]; then
  for f in "${snaps[@]:$KEEP_MIN}"; do
    if [ -n "$(find "$f" -mtime +"$KEEP_DAYS" -print 2>/dev/null)" ]; then
      rm -f "$f"
      echo "[$ts] pruned $(basename "$f")"
    fi
  done
fi
echo "[$ts] done: ${#snaps[@]} snapshot(s) kept"

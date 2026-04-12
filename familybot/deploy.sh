#!/usr/bin/env bash
# Run this script once on the Raspberry Pi to deploy familybot.
set -euo pipefail

DEST="/home/patrikbrach/familybot"

echo "=== Familybot deploy ==="

# 1. Copy project files
mkdir -p "$DEST"
rsync -av --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' \
      "$(dirname "$0")/" "$DEST/"

# 2. Create .env if missing
if [ ! -f "$DEST/.env" ]; then
    cp "$DEST/.env.example" "$DEST/.env"
    echo ""
    echo "⚠️  VIKTIGT: Fyll i dina API-nycklar i $DEST/.env innan du kör docker compose!"
    echo ""
fi

# 3. Create data dir
mkdir -p "$DEST/data"

echo ""
echo "=== Steg klara ==="
echo "Nästa steg:"
echo "  1. Redigera $DEST/.env med dina API-nycklar"
echo "  2. cd $DEST && docker compose build"
echo "  3. docker compose up -d bot"
echo "  4. Testa briefing: docker compose run --rm briefing python briefing.py"
echo "  5. Sätt upp cron (se README nedan):"
echo "     crontab -e"
echo "     Lägg till: 15 6 * * * cd $DEST && docker compose run --rm briefing python briefing.py >> /var/log/briefing.log 2>&1"

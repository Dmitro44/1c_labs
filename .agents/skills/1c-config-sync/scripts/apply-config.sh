#!/bin/bash
# Применение src/cf к файловой базе: освободить базу -> import -> apply -> CheckConfig
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
V8PATH="${V8PATH:-$(python3 -c "import json;print(json.load(open('$ROOT/.v8-project.json'))['v8path'])")}"
DBPATH="${DBPATH:-$(python3 -c "import json,os;print(os.path.join('$ROOT', json.load(open('$ROOT/.v8-project.json'))['databases'][0]['path']))")}"
cd "$ROOT"

echo "== Освобождаю базу ($DBPATH)..."
pkill -9 -f 'ibsrv|ibcmd' 2>/dev/null || true
if pgrep -fq '1cv8 DESIGNER|1cv8 ENTERPRISE' 2>/dev/null || pgrep -f '1cv8 (DESIGNER|ENTERPRISE)' >/dev/null 2>&1; then
  echo "ВНИМАНИЕ: открыты окна 1С пользователя (Конфигуратор/Предприятие) — завершаю их."
  pkill -f '1cv8 (DESIGNER|ENTERPRISE)' 2>/dev/null || true
  sleep 3
  pkill -9 -f '1cv8' 2>/dev/null || true
fi
sleep 1

echo "== Импорт и применение конфигурации..."
rm -rf /tmp/ibcmd_data
"$V8PATH/ibcmd" infobase config import --db-path="$DBPATH" --data=/tmp/ibcmd_data src/cf
"$V8PATH/ibcmd" infobase config apply --db-path="$DBPATH" --data=/tmp/ibcmd_data --force

if [[ "${1:-}" != "--no-check" ]]; then
  echo "== Проверка конфигурации (CheckConfig)..."
  "$V8PATH/1cv8" DESIGNER /F "$DBPATH" /CheckConfig -ThinClient -Server -OrdinaryApplication /Out /tmp/checkconfig.log /DisableStartupDialogs || true
  tail -2 /tmp/checkconfig.log
fi
echo "== Готово. База применена, больше никем не занята."

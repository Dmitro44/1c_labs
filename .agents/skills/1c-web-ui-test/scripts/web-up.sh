#!/bin/bash
# Поднять автономный веб-сервер 1С (ibsrv) на localhost:8314 с чистым data-каталогом
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
V8PATH="${V8PATH:-$(python3 -c "import json;print(json.load(open('$ROOT/.v8-project.json'))['v8path'])")}"
DBPATH="${DBPATH:-$(python3 -c "import json,os;print(os.path.join('$ROOT', json.load(open('$ROOT/.v8-project.json'))['databases'][0]['path']))")}"

if pgrep -f '1cv8 DESIGNER|1cv8 ENTERPRISE' >/dev/null 2>&1 || pgrep -fq '1cv8 DESIGNER' 2>/dev/null; then
  echo "ВНИМАНИЕ: открыт Конфигуратор/Предприятие — сервер может повиснуть на открытии базы."
  echo "Рекомендуется закрыть окна 1С и повторить. Продолжаю..."
fi

mkdir -p /tmp/1c_ss
if [[ ! -f /tmp/1c_ss/config.yml ]]; then
  "$V8PATH/ibcmd" server config init --address=localhost --port=8314 --base=/labs --name=labs --db-path="$DBPATH" --config=/tmp/1c_ss/config.yml
fi

pkill -9 -f ibsrv 2>/dev/null || true
sleep 1
rm -rf /tmp/1c_ss_data && mkdir -p /tmp/1c_ss_data
nohup "$V8PATH/ibsrv" --config=/tmp/1c_ss/config.yml --data=/tmp/1c_ss_data > /tmp/ibsrv.log 2>&1 &

for _ in $(seq 1 25); do
  sleep 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 2 http://localhost:8314/labs/ru_RU/ || true)
  if [[ "$code" == "200" ]]; then
    echo "OK: http://localhost:8314/labs/ru_RU/  (PID $(pgrep -f 'ibsrv --config' | head -1))"
    exit 0
  fi
done
echo "ОШИБКА: сервер не поднялся за 25с. Лог:"
tail -5 /tmp/ibsrv.log 2>/dev/null || echo "(лог пуст)"
exit 1

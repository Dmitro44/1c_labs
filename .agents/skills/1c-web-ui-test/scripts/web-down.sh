#!/bin/bash
# Остановить веб-сервер ibsrv и убедиться, что порт 8314 освободился
pkill -9 -f ibsrv 2>/dev/null || true
sleep 2
if pgrep -f ibsrv >/dev/null 2>&1; then
  echo "ВНИМАНИЕ: процесс ibsrv ещё жив:"
  pgrep -fl ibsrv
  exit 1
fi
echo "ibsrv остановлен."
if curl -s -o /dev/null -m 2 http://localhost:8314/ 2>/dev/null; then
  echo "ВНИМАНИЕ: порт 8314 всё ещё отвечает."
  exit 1
fi
echo "Порт 8314 закрыт, база свободна."

---
name: 1c-config-sync
description: Применение XML-исходников конфигурации 1С (src/cf) к файловой информационной базе через ibcmd и проверка CheckConfig. Использовать всегда, когда пользователь просит «применить/загрузить/обновить конфигурацию», «залей в базу», после любых правок XML в src/cf, а также при ошибках «Failed to get exclusive lock» / «Infobase may already be in use».
---

# Применение конфигурации 1С к базе (ibcmd)

Конфигурация хранится XML-исходниками в `src/cf` (иерархический формат), база — файловая. Платформа и пути берутся из `.v8-project.json` в корне проекта (v8path, databases[].path). Скрипты-обёртки уже учитывают это.

## Быстрый путь

```bash
bash .agents/skills/1c-config-sync/scripts/apply-config.sh          # kill 1С -> import -> apply -> CheckConfig
bash .agents/skills/1c-config-sync/scripts/apply-config.sh --no-check  # без CheckConfig
```

Переменные окружения `V8PATH` и `DBPATH` переопределяют платформу и базу.

## Ручная последовательность (если скрипта нет под рукой)

```bash
cd <корень проекта>
pgrep -fl '1cv8|ibsrv|ibcmd'          # кто держит базу
pkill -9 -f 'ibsrv|ibcmd'             # свои процессы — всегда
rm -rf /tmp/ibcmd_data
/opt/1cv8/8.5.1.1522/ibcmd infobase config import --db-path="$PWD/Labs_1s" --data=/tmp/ibcmd_data src/cf
/opt/1cv8/8.5.1.1522/ibcmd infobase config apply  --db-path="$PWD/Labs_1s" --data=/tmp/ibcmd_data --force
# проверка модулей/метаданных:
/opt/1cv8/8.5.1.1522/1cv8 DESIGNER /F "$PWD/Labs_1s" /CheckConfig -ThinClient -Server -OrdinaryApplication /Out /tmp/check.log /DisableStartupDialogs
```

## Правила

- Перед import/apply база должна быть СВОБОДНА. Держат: Конфигуратор и Предприятие пользователя, веб-сервер ibsrv, зависший ibcmd. Окон пользователя это касается в первую очередь — завершай их только с ведома пользователя (в этом проекте пользователь разрешил «в конце закрывай»), и обязательно сообщи в ответе, что его окна были закрыты.
- Import падает на первом же некорректном XML — имя файла в ошибке указывает, какой объект править. Ошибка «Different property and XDTO data item: Property X» почти всегда означает неверное значение/имя свойства в Form.xml (см. скилл 1c-platform-quirks).
- CheckConfig сам держит базу, пока работает; запускай его ПОСЛЕ apply, не параллельно.
- **Обязательное завершение работы**: не оставлять от себя процессов, работающих с базой (ibsrv, ibcmd). Если поднимал веб-сервер для проверки — остановить (`bash .agents/skills/1c-web-ui-test/scripts/web-down.sh`) и удостовериться, что порт 8314 закрыт и база свободна; в финальном ответе подтвердить это пользователю. Исключение — только явная просьба пользователя оставить сервер.
- Если apply прошёл, но поведение старое — проверь, что правил именно тот файл, который в src/cf (src — источник истины, база — приёмник).

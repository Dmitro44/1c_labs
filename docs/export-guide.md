# Гайд для ИИ-ассистента: экспорт и перенос проекта 1С

Документ самодостаточный: выполняя его сверху вниз, другая нейросеть сможет выгрузить
этот проект 1С в любом формате и развернуть его на другой машине. Все команды ниже
проверены реальными прогонами на этом проекте (платформа 1С 8.5.1.1522, macOS).

## 0. Контекст проекта

| Что | Где |
|---|---|
| Корень проекта | `~/Documents/University/7_SEM/TOFD` (далее `$ROOT`) |
| Платформа | `/opt/1cv8/8.5.1.1522` (утилиты `ibcmd`, `ibsrv`, `1cv8`) — путь также в `.v8-project.json` → `v8path` |
| Файловая информационная база | `$ROOT/Labs_1s` (главный файл `1Cv8.1CD`) |
| XML-исходники конфигурации | `$ROOT/src/cf` — источник истины, иерархический формат |
| Сборка форм (DSL→XML) | `$ROOT/build` + компилятор `cc-1c-skills` (клонируется отдельно, в git не входит) |
| Git-remote | `git@github.com:Dmitro44/1c_labs.git`, ветки `master` и `tofd-labs` |
| Готовые скрипты | `.agents/skills/1c-config-sync/scripts/apply-config.sh`, `.agents/skills/1c-web-ui-test/scripts/web-{up,down}.sh` |

Требуемая версия платформы на приёмнике: 8.5.1.1522 или новее (конфигурация в режиме совместимости 8.5.1).

## 1. Железное правило: база должна быть свободна

Любая операция экспорта/импорта требует, чтобы файловую базу никто не держал.

```bash
pgrep -fl '1cv8|ibsrv|ibcmd'    # кто держит базу прямо сейчас
pkill -9 -f 'ibsrv|ibcmd'       # свои процессы — останавливать всегда
```

Окна пользователя (`1cv8 DESIGNER` / `1cv8 ENTERPRISE`) закрывать только с его ведома —
в несохранённой сессии Конфигуратора могут быть правки. Признак занятости базы:
ошибки `Failed to get exclusive lock` / `Infobase may already be in use`.
Особый случай: веб-сервер `ibsrv` при занятой базе отвечает на статику (HTTP 200),
но сессию не отдаёт и виснет — проверяй `lsof -nP -iTCP:8314 -sTCP:LISTEN`.

## 2. Три формата экспорта (команды проверены)

Из каталога проекта (`cd $ROOT`), база свободна:

### A. XML-исходники — основной формат (для git и правок)

```bash
/opt/1cv8/8.5.1.1522/ibcmd infobase config export --db-path="$PWD/Labs_1s" /tmp/export_xml
```

Получаем иерархию `Catalogs/ Documents/ Enums/ InformationRegisters/ Subsystems/ …`
плюс `Configuration.xml` и `ConfigDumpInfo.xml`. Именно в этом формате хранится `src/cf`.

### B. Файл конфигурации .cf — только конфигурация, без данных

```bash
/opt/1cv8/8.5.1.1522/ibcmd infobase config save --db-path="$PWD/Labs_1s" /tmp/labs.cf
```

### C. Выгрузка базы .dt — данные + конфигурация одним файлом

```bash
/opt/1cv8/8.5.1.1522/ibcmd infobase dump --db-path="$PWD/Labs_1s" /tmp/labs.dt
```

ВНИМАНИЕ: команда называется `dump`, а НЕ `unload` (несуществующая `unload` выдаёт
невнятную подсказку «The command is incomplete»). Не повторяйте эту ошибку.

GUI-эквиваленты в Конфигураторе: «Конфигурация → Выгрузить конфигурацию в файлы»,
«Конфигурация → Сохранить конфигурацию в файл», «Администрирование → Выгрузить информационную базу».

## 3. Развертывание на приёмнике (проверено)

```bash
# новая пустая файловая база:
/opt/1cv8/8.5.1.1522/ibcmd infobase create --db-path=/path/to/new_base

# вариант 1: из .dt (данные + конфигурация):
/opt/1cv8/8.5.1.1522/ibcmd infobase restore --db-path=/path/to/new_base /tmp/labs.dt

# вариант 2: из .cf (только конфигурация):
/opt/1cv8/8.5.1.1522/ibcmd infobase config load --db-path=/path/to/new_base /tmp/labs.cf

# вариант 3: из XML-исходников (каталог с Configuration.xml):
rm -rf /tmp/ibcmd_data
/opt/1cv8/8.5.1.1522/ibcmd infobase config import --db-path=/path/to/new_base --data=/tmp/ibcmd_data src/cf
/opt/1cv8/8.5.1.1522/ibcmd infobase config apply  --db-path=/path/to/new_base --data=/tmp/ibcmd_data --force
```

Вариант 3 на этой машине автоматизирован: `bash .agents/skills/1c-config-sync/scripts/apply-config.sh`
(сам освобождает базу, делает import+apply и контрольную проверку `/CheckConfig`).

Запуск на приёмнике:

```bash
# macOS / Linux:
/opt/1cv8/8.5.1.1522/1cv8 DESIGNER  /F /path/to/Labs_1s /L ru
/opt/1cv8/8.5.1.1522/1cv8 ENTERPRISE /F /path/to/Labs_1s /L ru
# Windows: "C:\Program Files\1cv8\<версия>\bin\1cv8.exe" ENTERPRISE /F "C:\путь\Labs_1s" /L ru
```

## 4. Экспорт «всё сразу» архивом (для человека, без 1С на приёмнике)

```bash
cd ~/Documents/University/7_SEM
zip -r -q TOFD_1c.zip TOFD/Labs_1s TOFD/src TOFD/build TOFD/lab2_gemini.md
```

База копируется консистентной только при СВОБОДНОЙ базе (см. §1). Не включать:
`cc-1c-skills/` (чужой git-репозиторий, 46 МБ), `.venv-1c/`, `.DS_Store`, служебные
файлы базы (`*.cfl`, `1Cv8Log/`, `1Cv8.1CD.backup_*`, `1Cv8snc.1CD`, `1Cv8.1CL`, `1Cv8.cgr`) —
полный список в `.gitignore`.

## 5. Git

```bash
git add -A && git commit -m "…" && git push origin tofd-labs
git push origin tofd-labs:master   # мастер держим равным ветке (после rebase это fast-forward)
```

## 6. Грабли (реально встречались)

- **Занятая база** — см. §1; самый коварный вариант: Конфигуратор в монопольном режиме
  (ibsrv даёт 200 и виснет на сессии).
- **Кодировки**: XML/BSL файлы — UTF-8 ровно с ОДНИМ BOM; двойной BOM даёт «Document is empty».
- **Версия форм**: form-compile эмитит `version="2.17"`, платформа 8.5 требует `2.21` —
  заменять после компиляции.
- **`ibcmd` после жёсткого убийства ibsrv**: каталог `--data` веб-сервера пересоздавать чистым.
- После любого импорта запускать проверку:
  `1cv8 DESIGNER /F <база> /CheckConfig -ThinClient -Server -OrdinaryApplication /Out check.log /DisableStartupDialogs`.
- Специфика платформы 8.5 (сортировки динсписков, левые закладки `TabsOnLeftHorizontal`,
  периодичность регистров) — справочник `.agents/skills/1c-platform-quirks/SKILL.md`.

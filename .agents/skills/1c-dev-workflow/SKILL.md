---
name: 1c-dev-workflow
description: Полный цикл разработки в конфигурации «Кадровый учёт БГУИР»: структура src/cf, добавление объектов метаданных, форм, кнопок/команд, реквизитов и отчётов, наполнение базы документами, применение через ibcmd, проверка в веб-клиенте и освобождение базы. Использовать при задачах «добавь справочник/документ/отчёт», «сделай кнопку», «добавь реквизит», «почему не применяется конфигурация», «как работать с 1С в этом проекте».
---

# Как работать с 1С в этом проекте

Практическое руководство для LLM-агента: где что лежит, как добавить объект/форму/кнопку,
как довести изменение до базы и как проверить результат, не сломав чужую работу.

**Мелкая задача — кнопка, перенос поля, заголовок, видимость? Сразу в §0.2 «Быстрые рецепты».**
Там готовые скрипты и минимум шагов; остальные разделы — для создания объектов с нуля.

## 0. Главные правила

1. **Источник истины — `src/cf`** (иерархическая выгрузка XML). База `Labs_1s` — приёмник.
   Правки в Конфигураторе без выгрузки в `src/cf` потеряются при следующем `apply`.
2. **Любая правка XML/BSL заканчивается применением**:
   `apply-config.sh` → `CheckConfig` → (если нужно) проверка в веб-клиенте.
3. **Отчёты только читают данные.** В модулях отчётов не должно быть
   `СоздатьЭлемент`, `СоздатьДокумент`, `.Записать(`, `.Удалить(`, `Движения.`.
   Демо-данные вводятся документами/обработкой, а не кодом отчёта.
4. **После любой работы с базой освободить её**: остановить `ibsrv`, `ibcmd`, не оставлять
   свои окна `1cv8`. Проверить: `lsof -nP -iTCP:8314 -sTCP:LISTEN` пусто.
5. **Не перезаписывать чужую работу.** Перед `git pull`, удалением файлов и массовыми
   заменами смотреть `git status` и `git diff`; незнакомые изменения считать работой пользователя.
6. **Минимальные хирургические правки.** Сначала прочитать соседний рабочий код и повторить
   его стиль, а не изобретать новую архитектуру.

### 0.1 Алгоритм работы над задачей

1. **Понять задачу и найти аналог.** `grep` по `src/cf` и `build/`: почти всегда уже есть
   похожая форма, отчёт или документ, с которого можно взять структуру.
2. **Проверить состояние репозитория и базы.** `git status --short`, `pgrep -fl '1cv8|ibsrv'`.
   Незакоммиченные чужие правки не перезаписывать.
3. **Спланировать минимальный набор изменений**: объект → форма → команда → модуль →
   регистрация в подсистеме. Не добавлять «на будущее» лишние сущности.
4. **Внести правки** (инструменты из `cc-1c-skills` или ручной XML/BSL).
5. **Применить и проверить**: `apply-config.sh`, при ошибке — исправить и повторить.
6. **Проверить поведение** в веб-клиенте, если задача про UI/отчёт.
7. **Освободить базу** и отчитаться: что изменено, как проверено.
8. Коммит/пуш — только если пользователь попросил (или это часть его задачи).

## 0.2 Быстрые рецепты (начинать здесь)

Куда лезть под задачу:

| Задача | Что править |
|---|---|
| кнопка/команда | `Forms/<Форма>/Ext/Form.xml` + `Ext/Form/Module.bsl` |
| поле, группа, страница, порядок | `Forms/<Форма>/Ext/Form.xml` |
| новый реквизит | `<Объект>.xml` (`meta-edit`), затем поле в `Form.xml` |
| логика, запросы, расчёты | `Ext/Form/Module.bsl` или `Ext/ObjectModule.bsl` |
| видимость команды в разделе | `Subsystems/.../Ext/CommandInterface.xml` |
| состав подсистемы | `Subsystems/<Имя>/Subsystems/<Дочерняя>.xml` (`<Content>`) |

**Важно:** если форма собирается из JSON DSL (`build/*.json` и `form-compile`), правь JSON
и перекомпилируй. Иначе следующая компиляция затрёт ручные правки XML. Проверка:

```bash
grep -rl "ЗаголовокИлиИмяЭлемента" build/*.json 2>/dev/null
```

### 0.2.1 Добавить кнопку с действием — за 2 шага

```bash
# 1. кнопка + команда + заготовка обработчика
python3 .agents/skills/1c-dev-workflow/scripts/add-button.py \
  -Form "src/cf/Documents/ПриемНаРаботу/Forms/ФормаДокумента/Ext/Form.xml" \
  -Name ПроверитьДанные -Title "Проверить данные…" -Action ПроверитьДанные \
  -To ФормаКоманднаяПанель \
  -Module "src/cf/Documents/ПриемНаРаботу/Forms/ФормаДокумента/Ext/Form/Module.bsl"

# 2. вписать код в процедуру ПроверитьДанные в Module.bsl
```

Имя кнопки/команды должно быть новым: если оно уже занято, скрипт откажется работать.
Для кнопки в командной панели таблицы укажите `-To <ИмяТаблицы>КоманднаяПанель`
(точное имя — в `-List`).

Скрипт сам:

- находит командную панель (`-To`; по умолчанию `ФормаКоманднаяПанель`);
- добавляет `<Button>` и `<Command>` с уникальными `id`;
- при `-Module` создаёт `&НаКлиенте Процедура <Action>(Команда)` в области
  «ОбработчикиКомандФормы».

Проверить и применить:

```bash
python3 cc-1c-skills/.claude/skills/form-validate/scripts/form-validate.py \
  -FormPath "src/cf/Documents/ПриемНаРаботу/Forms/ФормаПросмотраСтавок/Ext/Form.xml"
bash .agents/skills/1c-config-sync/scripts/apply-config.sh
```

Если скрипта под рукой нет — ручной шаблон в §5.2.

### 0.2.2 Перенести поле / кнопку / группу

```bash
# 1. посмотреть, что где лежит
python3 .agents/skills/1c-dev-workflow/scripts/move-element.py \
  -Form "src/cf/Documents/ПриемНаРаботу/Forms/ФормаДокумента/Ext/Form.xml" -List

# 2. перенести (в конец группы) или первым элементом (-Index 0)
python3 .agents/skills/1c-dev-workflow/scripts/move-element.py \
  -Form "src/cf/Documents/ПриемНаРаботу/Forms/ФормаДокумента/Ext/Form.xml" \
  -Element ВидФинансирования -To ГруппаШапка -Index 0
```

Скрипт переносит блок целиком (вместе с дочерними элементами и `id`), сохраняет
отступы и порядок. После переноса — `form-validate.py` и `apply-config.sh`.

Куда можно переносить: любая `UsualGroup`, `Page`, `Table`, `AutoCommandBar` (имя из `-List`).
Нельзя переносить элемент внутрь самого себя.

### 0.2.3 Поменять заголовок, обработчик, видимость

Заголовок (менять и у кнопки, и у команды, если есть оба):

```xml
<Title>
	<v8:item>
		<v8:lang>ru</v8:lang>
		<v8:content>Новый текст</v8:content>
	</v8:item>
</Title>
```

Обработчик: `<Action>НовоеИмя</Action>` в `<Command>` и процедура `Процедура НовоеИмя(Команда)`
в модуле — имена обязаны совпадать.

Скрыть/показать:

```xml
<Visible>false</Visible>
```

или из кода: `Элементы.ИмяЭлемента.Видимость = Ложь;`

### 0.2.4 Добавить поле в форму

1. Если реквизита ещё нет:

```bash
python3 cc-1c-skills/.claude/skills/meta-edit/scripts/meta-edit.py \
  -ObjectPath src/cf/Catalogs/Пропуска.xml -Operation add-attribute -Value "Комментарий: String(200)"
```

2. В `Form.xml` скопировать соседний `<InputField>` и заменить:

```xml
<InputField name="Комментарий" id="42">
	<DataPath>Объект.Комментарий</DataPath>
	<Title>
		<v8:item>
			<v8:lang>ru</v8:lang>
			<v8:content>Комментарий</v8:content>
		</v8:item>
	</Title>
	<ExtendedTooltip name="КомментарийРасширеннаяПодсказка" id="43"/>
</InputField>
```

3. Вставить блок в нужный `<ChildItems>` (порядок = порядок на форме), `id` — уникальные.
4. `apply-config.sh`.

### 0.2.5 Перенести отчёт/объект в другую подсистему

Вырезать строку из `<Content>` одной подсистемы и вставить в другую:

```xml
<xr:Item xsi:type="xr:MDObjectRef">Report.ШтатноеРасписание</xr:Item>
```

Или добавить инструментом:

```bash
python3 cc-1c-skills/.claude/skills/subsystem-edit/scripts/subsystem-edit.py \
  -SubsystemPath src/cf/Subsystems/КадровыйУчет/Subsystems/Отчеты.xml \
  -Operation add-content -Value "Report.ШтатноеРасписание"
```

После — `apply-config.sh`; проверить, что отчёт виден в нужном разделе.

### 0.2.6 Минимальная проверка быстрой правки

```bash
python3 cc-1c-skills/.claude/skills/form-validate/scripts/form-validate.py -FormPath "<Form.xml>"
bash .agents/skills/1c-config-sync/scripts/apply-config.sh   # No errors found
# для UI-задач: web-up.sh -> открыть форму -> web-down.sh
```

## 1. Карта проекта

```
TOFD/
├── .v8-project.json          # путь к платформе и базе (не хардкодить!)
├── Labs_1s/                  # файловая информационная база (1Cv8.1CD)
├── src/cf/                   # исходники конфигурации (главное)
│   ├── Configuration.xml     # корень: ChildObjects со всеми объектами
│   ├── Catalogs/<Имя>.xml
│   ├── Documents/<Имя>.xml
│   ├── Reports/<Имя>.xml
│   ├── InformationRegisters/
│   ├── AccumulationRegisters/
│   ├── Enums/
│   ├── CommonModules/
│   ├── Subsystems/<Имя>.xml
│   │   └── <Имя>/Subsystems/<Дочерняя>.xml
│   └── Ext/ManagedApplicationModule.bsl
├── build/                    # JSON-исходники форм для form-compile и служебные файлы
├── .agents/skills/           # проектные скиллы (этот и смежные)
└── cc-1c-skills/             # инструменты: form-compile, meta-compile, meta-edit, ...
```

Платформа и база берутся из `.v8-project.json`:

```bash
python3 - <<'PY'
import json
p=json.load(open('.v8-project.json'))
print(p['v8path'])
print(p['databases'][0]['path'])
PY
```

В этом проекте: платформа `/opt/1cv8/8.5.1.1522`, база `Labs_1s`,
веб-клиент `http://localhost:8314/labs/ru_RU/`.

Смежные скиллы (читать при деталях):

| Скилл | Когда |
|---|---|
| `1c-config-sync` | применить `src/cf` к базе, ошибки блокировки |
| `1c-form-build` | JSON DSL форм, `form-compile`, регистрация формы |
| `1c-platform-quirks` | странное поведение 8.5: сортировки, XDTO, формы |
| `1c-web-ui-test` | запуск веб-клиента и визуальная проверка |

## 2. Обязательный рабочий цикл

```bash
cd <корень проекта>

# 1. Убедиться, что база свободна
pgrep -fl '1cv8|ibsrv|ibcmd'

# 2. Применить исходники: закрывает окна 1С, import + apply + CheckConfig
bash .agents/skills/1c-config-sync/scripts/apply-config.sh
# без CheckConfig:
# bash .agents/skills/1c-config-sync/scripts/apply-config.sh --no-check
```

Что делает скрипт:

1. `pkill` для `ibsrv`/`ibcmd` и окон `1cv8 DESIGNER|ENTERPRISE`;
2. `ibcmd infobase config import --db-path=Labs_1s --data=/tmp/ibcmd_data src/cf`;
3. `ibcmd infobase config apply ... --force`;
4. `1cv8 DESIGNER /F Labs_1s /CheckConfig ...`, лог `/tmp/checkconfig.log`.

Ожидаемый результат: `Database configuration successfully updated` и `No errors found`.

Ручной вариант (если скрипта нет):

```bash
V8=/opt/1cv8/8.5.1.1522
DB="$PWD/Labs_1s"
pkill -9 -f 'ibsrv|ibcmd' 2>/dev/null || true
rm -rf /tmp/ibcmd_data
"$V8/ibcmd" infobase config import --db-path="$DB" --data=/tmp/ibcmd_data src/cf
"$V8/ibcmd" infobase config apply  --db-path="$DB" --data=/tmp/ibcmd_data --force
"$V8/1cv8" DESIGNER /F "$DB" /CheckConfig -ThinClient -Server -OrdinaryApplication \
  /Out /tmp/check.log /DisableStartupDialogs
cat /tmp/check.log
```

Важно: `CheckConfig` держит базу, пока работает. Не запускать его параллельно с `apply`
и не поднимать веб-сервер, пока он не завершился.

## 3. Добавить объект метаданных

### 3.1 Через `meta-compile` (рекомендуется)

`cc-1c-skills/.claude/skills/meta-compile/scripts/meta-compile.py` генерирует XML объекта,
модули и **сам регистрирует объект в `Configuration.xml`**.

```bash
cat > /tmp/new_catalog.json <<'JSON'
{
  "type": "Catalog",
  "name": "Пропуска",
  "synonym": "Пропуска",
  "codeLength": 9,
  "descriptionLength": 100,
  "attributes": [
    "Номер: String(20) | req, index",
    "ДатаВыдачи: Date",
    "Сотрудник: CatalogRef.Сотрудники",
    "Активен: Boolean"
  ],
  "tabularSections": {
    "Строки": ["Товар: String(100)", "Количество: Number(10,3)"]
  }
}
JSON

python3 cc-1c-skills/.claude/skills/meta-compile/scripts/meta-compile.py \
  -JsonPath /tmp/new_catalog.json -OutputDir src/cf
```

Документ:

```json
{
  "type": "Document",
  "name": "Перевод",
  "attributes": [
    "Сотрудник: CatalogRef.Сотрудники | req",
    "ДатаПеревода: Date | req",
    "Оклад: Number(10,2)"
  ],
  "tabularSections": { "Начисления": ["Надбавка: CatalogRef.Надбавки", "Сумма: Number(10,2)"] },
  "registerRecords": ["AccumulationRegister.РегистрУчетаСотрудников"]
}
```

Регистр сведений:

```json
{
  "type": "InformationRegister",
  "name": "ПропускаСотрудников",
  "periodicity": "Day",
  "dimensions": ["Сотрудник: CatalogRef.Сотрудники | master"],
  "resources": ["Количество: Number(5,0)"]
}
```

Отчёт:

```json
{ "type": "Report", "name": "ШтатноеРасписание" }
```

После генерации:

```bash
# meta-compile пишет CRLF — привести к LF, как остальные файлы проекта
python3 - <<'PY'
p='src/cf/Catalogs/Пропуска.xml'
s=open(p,encoding='utf-8-sig').read().replace('\r\n','\n')
open(p,'w',encoding='utf-8-sig',newline='\n').write(s)
PY
```

Проверить, что объект появился в `Configuration.xml`:

```bash
grep -n "Пропуска" src/cf/Configuration.xml
```

Типы и флаги описаны в `cc-1c-skills/.claude/skills/meta-compile/SKILL.md`
(`req`, `index`, `nonneg`, `master`, `mainFilter` и т.д.).

### 3.2 Если объект нестандартный — копировать ближайший

`meta-compile` не покрывает 100% свойств. Тогда:

1. скопировать XML похожего объекта (например, `Catalogs/Должности.xml`);
2. заменить `Name`, `Synonym`, все `uuid` и `TypeId`/`ValueId` на новые (`uuid.uuid4()`);
3. поправить `InternalInfo` (имена `CatalogObject.X`, `CatalogRef.X`, ...);
4. добавить запись в `Configuration.xml` в правильный раздел `<ChildObjects>`.

Скрипт массовой замены UUID:

```bash
python3 - <<'PY'
import re, uuid
src='src/cf/Catalogs/Должности.xml'
dst='src/cf/Catalogs/Пропуска.xml'
s=open(src,encoding='utf-8-sig').read()
s=s.replace('Должности','Пропуска')
s=re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
         lambda m: str(uuid.uuid4()), s)
open(dst,'w',encoding='utf-8-sig').write(s)
PY
```

### 3.3 Включить объект в подсистему

`meta-compile` этого не делает. Либо инструментом:

```bash
python3 cc-1c-skills/.claude/skills/subsystem-edit/scripts/subsystem-edit.py \
  -SubsystemPath src/cf/Subsystems/КадровыйУчет/Subsystems/Отчеты.xml \
  -Operation add-content -Value "Report.ШтатноеРасписание"
```

Либо вручную в `<Content>` подсистемы:

```xml
<xr:Item xsi:type="xr:MDObjectRef">Catalog.Пропуска</xr:Item>
```

Для видимости в панели раздела — команда в `Subsystems/<Имя>/Ext/CommandInterface.xml`.
Проще всего `interface-edit.py` с операцией `place` (значение — JSON!):

```bash
python3 cc-1c-skills/.claude/skills/interface-edit/scripts/interface-edit.py \
  -CIPath src/cf/Subsystems/КадровыйУчет/Ext/CommandInterface.xml \
  -Operation place \
  -Value '{"command":"Catalog.Пропуска.StandardCommand.OpenList","group":"NavigationPanelOrdinary"}'
```

Итог в XML:

```xml
<Command name="Catalog.Пропуска.StandardCommand.OpenList">
	<CommandGroup>NavigationPanelOrdinary</CommandGroup>
	<Placement>Auto</Placement>
</Command>
```

Операции: `hide`/`show` (имя команды), `place` (JSON `{command, group}`),
`order` (JSON `{group, commands:[...]}`), `subsystem-order` (массив),
`group-order` (массив групп).

## 4. Добавить форму

### 4.1 Каркас формы

```bash
python3 cc-1c-skills/.claude/skills/form-add/scripts/form-add.py \
  -ObjectPath src/cf/Catalogs/Пропуска.xml \
  -FormName ФормаЭлемента -Synonym "Форма элемента" \
  -Purpose Object -SetDefault
```

`Purpose`: `Object`, `List`, `Choice`, `Folder`, `FolderChoice`, `Custom`
(для отчёта/обработки — `Object`). `-SetDefault` прописывает форму как основную.

### 4.2 Форма из JSON DSL

Сложные формы (таблицы, группы, кнопки) удобнее описывать JSON и компилировать:

```bash
python3 cc-1c-skills/.claude/skills/form-compile/scripts/form-compile.py \
  -JsonPath build/my_form.json \
  -OutputPath "src/cf/Catalogs/Пропуска/Forms/ФормаЭлемента/Ext/Form.xml"

# form-compile пишет version="2.17" и CRLF — привести к формату проекта
sed -i '' 's/version="2\.17"/version="2.21"/' \
  "src/cf/Catalogs/Пропуска/Forms/ФормаЭлемента/Ext/Form.xml"
python3 - <<'PY'
p='src/cf/Catalogs/Пропуска/Forms/ФормаЭлемента/Ext/Form.xml'
s=open(p,encoding='utf-8-sig').read().replace('\r\n','\n')
open(p,'w',encoding='utf-8-sig',newline='\n').write(s)
PY
```

Минимальный JSON:

```json
{
  "title": "Пропуск",
  "events": { "OnCreateAtServer": "ПриСозданииНаСервере" },
  "elements": [
    { "autoCmdBar": "ФормаКоманднаяПанель", "children": [
      { "button": "Записать", "command": "Записать", "title": "Записать", "defaultButton": true }
    ]},
    { "group": "vertical", "name": "ГруппаРеквизиты", "united": true, "children": [
      { "input": "Номер", "path": "Объект.Номер" },
      { "input": "ДатаВыдачи", "path": "Объект.ДатаВыдачи" }
    ]}
  ],
  "attributes": [
    { "name": "Объект", "type": "CatalogObject.Пропуска", "main": true }
  ],
  "commands": [
    { "name": "Записать", "title": "Записать", "action": "Записать" }
  ]
}
```

Правила, проверенные на 8.5:

- `"autoCmdBar"` — первым элементом **внутри** `elements`, не на верхнем уровне;
- `"alwaysHorizontal"` или `"vertical"`, значения `"horizontalIfPossible"` избегать;
- `"picture"` у кнопок не задавать (XDTO-ошибка `Property Picture`);
- `Action` команды = точное имя процедуры в `Module.bsl`, иначе кнопка молча не работает;
- после компиляции проверить, что `<Form>Имя</Form>` попало в объект на нужный уровень
  (иногда компилятор вставляет внутрь табличной части).

## 5. Добавить кнопку и команду

> Для существующей формы быстрее `scripts/add-button.py` — см. §0.2.1. Ниже — ручные способы.

### 5.1 Через JSON DSL (новые формы)

```json
"commands": [
  { "name": "Добавить", "title": "Добавить", "action": "Добавить" }
],
"elements": [
  { "autoCmdBar": "ФормаКоманднаяПанель", "children": [
    { "button": "Добавить", "command": "Добавить", "title": "Добавить" }
  ]}
]
```

В модуле формы:

```bsl
&НаКлиенте
Процедура Добавить(Команда)
	// обработчик
КонецПроцедуры
```

`form-compile` сам создаст `<Command>` и `<Button>` с нужными именами.

### 5.2 Правкой `Form.xml` (существующая форма)

Кнопка в командную панель таблицы:

```xml
<AutoCommandBar name="СтавкиКоманднаяПанель" id="3">
	<Autofill>false</Autofill>
	<ChildItems>
		<Button name="ДобавитьСтавки" id="39">
			<Type>CommandBarButton</Type>
			<CommandName>Form.Command.ДобавитьСтавки</CommandName>
			<Title>
				<v8:item>
					<v8:lang>ru</v8:lang>
					<v8:content>Добавить ставки…</v8:content>
				</v8:item>
			</Title>
			<ExtendedTooltip name="ДобавитьСтавкиРасширеннаяПодсказка" id="40"/>
		</Button>
	</ChildItems>
</AutoCommandBar>
```

Команда — в конец `<Form>`, перед `</Form>`:

```xml
<Commands>
	<Command name="ДобавитьСтавки" id="41">
		<Title>
			<v8:item>
				<v8:lang>ru</v8:lang>
				<v8:content>Добавить ставки…</v8:content>
			</v8:item>
		</Title>
		<Action>ДобавитьСтавки</Action>
	</Command>
</Commands>
```

Требования:

- `id` новых элементов — уникальные числа, больше максимального в файле;
- `CommandName` = `Form.Command.<Имя команды>`;
- `Action` = имя процедуры в `Module.bsl`;
- для кнопки в шапке формы использовать `ФормаКоманднаяПанель`, для таблицы — её
  `AutoCommandBar` (`<Таблица>КоманднаяПанель`).

### 5.3 Обработчик в модуле формы

```bsl
&НаКлиенте
Процедура ДобавитьСтавки(Команда)
	ОповещениеОЗакрытии = Новый ОписаниеОповещения("ПослеДобавленияСтавок", ЭтотОбъект);
	ОткрытьФорму("Документ.ВводШтатнойЕдиницы.Форма.ФормаДокумента", , ЭтотОбъект, , , , ОповещениеОЗакрытии);
КонецПроцедуры

&НаКлиенте
Процедура ПослеДобавленияСтавок(РезультатЗакрытия, ДопПараметры) Экспорт
	ЗаполнитьСтавки();
КонецПроцедуры
```

Серверные действия — в `&НаСервере`-процедурах, клиентские — в `&НаКлиенте`.
Вызов серверной процедуры из клиентской — обычным вызовом (платформа сходит на сервер).

## 6. Кнопка «Добавить», которая создаёт объект

### 6.1 Открыть форму нового объекта (правильный путь для UI)

```bsl
&НаКлиенте
Процедура ДобавитьСотрудника(Команда)
	// без «Значения» стандартная форма открывается как новый элемент
	Оповещение = Новый ОписаниеОповещения("ПослеСозданияСотрудника", ЭтотОбъект);
	ОткрытьФорму("Справочник.Сотрудники.Форма.ФормаЭлемента", , ЭтотОбъект, , , , Оповещение);
КонецПроцедуры

&НаКлиенте
Процедура ПослеСозданияСотрудника(Результат, ДопПараметры) Экспорт
	Элементы.Список.Обновить();
КонецПроцедуры
```

Для документа — `"Документ.ПриемНаРаботу.Форма.ФормаДокумента"`.
Так пользователь заполняет объект сам, а проведение/запись выполняет платформа.

### 6.2 Создать объект кодом (только обработка/загрузчик, не отчёт)

```bsl
&НаСервере
Функция СоздатьПропуск(Сотрудник, ДатаВыдачи)
	Объект = Справочники.Пропуска.СоздатьЭлемент();
	Объект.Сотрудник = Сотрудник;
	Объект.ДатаВыдачи = ДатаВыдачи;
	Объект.Записать();
	Возврат Объект.Ссылка;
КонецФункции
```

Правило проекта: такой код живёт в обработке (`DataProcessors/...`) или общем модуле-загрузчике,
но **не в модуле отчёта**. Отчёт при формировании не должен менять базу.

### 6.3 Добавить строку в таблицу формы

```bsl
&НаКлиенте
Процедура ДобавитьСтроку(Команда)
	НоваяСтрока = Элементы.Ставки.Добавить();
	НоваяСтрока.Ставка = 1;
КонецПроцедуры
```

Для табличной части объекта:

```bsl
&НаСервере
Процедура ДобавитьСтрокуНаСервере()
	НоваяСтрока = Объект.Начисления.Добавить();
	НоваяСтрока.Сумма = 0;
КонецПроцедуры
```

## 7. Добавить реквизит / измерение / ресурс

Инструментом:

```bash
python3 cc-1c-skills/.claude/skills/meta-edit/scripts/meta-edit.py \
  -ObjectPath src/cf/Catalogs/Пропуска.xml \
  -Operation add-attribute -Value "Комментарий: String(200)"
```

Другие операции: `add-ts`, `add-dimension`, `add-resource`, `add-column`, `add-enumValue`,
`modify-attribute`, `remove-attribute`.

Вручную: скопировать соседний `<Attribute uuid="...">` / `<Dimension uuid="...">` блок,
заменить `Name`, `Synonym`, `Type` и `uuid`. Для строки — `xs:string` + `StringQualifiers`,
для числа — `xs:decimal` + `NumberQualifiers`.

После правки обязательно `apply-config.sh` — иначе в базе останется старый состав реквизитов.

## 8. Добавить отчёт

1. Создать объект:

```bash
echo '{"type":"Report","name":"ШтатноеРасписание","synonym":"Штатное расписание"}' > /tmp/report.json
python3 cc-1c-skills/.claude/skills/meta-compile/scripts/meta-compile.py \
  -JsonPath /tmp/report.json -OutputDir src/cf
```

2. Добавить форму отчёта:

```bash
python3 cc-1c-skills/.claude/skills/form-add/scripts/form-add.py \
  -ObjectPath src/cf/Reports/ШтатноеРасписание.xml \
  -FormName ФормаОтчета -Synonym "Форма отчета" -Purpose Object -SetDefault
```

3. Собрать форму из DSL (фильтры + `SpreadSheetDocumentField`):

```json
{
  "title": "Штатное расписание",
  "elements": [
    { "autoCmdBar": "ФормаКоманднаяПанель", "children": [
      { "button": "Сформировать", "command": "Сформировать", "title": "Сформировать…", "defaultButton": true }
    ]},
    { "group": "vertical", "name": "ГруппаФильтры", "united": true, "children": [
      { "input": "Дата", "path": "Дата", "width": 14 }
    ]},
    { "spreadsheet": "Результат", "path": "Результат", "titleLocation": "none",
      "readOnly": true, "output": "Disable", "protection": true }
  ],
  "attributes": [
    { "name": "Дата", "type": "date" },
    { "name": "Результат", "type": "mxl:SpreadsheetDocument" }
  ],
  "commands": [
    { "name": "Сформировать", "title": "Сформировать…", "action": "Сформировать" }
  ]
}
```

4. Модуль формы: запрос → `Результат.Очистить()` → заполнение областей → widths/объединения/рамки.
   Готовые образцы: `Reports/ТарифныеОклады`, `Reports/СвободныеСтавки`, `Reports/РаботающиеСотрудники`.
5. Включить в подсистему `КадровыйУчет/Subsystems/Отчеты.xml` (см. п. 3.3).

## 9. Данные — в базу, а не в код

Демонстрационные и рабочие данные должны существовать как объекты базы:

- справочники — элементы (`Справочники.X.СоздатьЭлемент()`), но только в загрузчике/обработке;
- движения — документы с проведением (`Движения.Регистр.Записать()` в `ОбработкаПроведения`);
- обработка `DataProcessors/ЗагрузкаДемоДанных` — штатное место для массового наполнения;
- запуск загрузчика в этом проекте: параметр `/C ЗагрузитьДемоДанные`
  (`Ext/ManagedApplicationModule.bsl`).

Проверка, что в отчётах нет записи:

```bash
grep -rn "СоздатьЭлемент\|СоздатьДокумент\|\.Записать(\|\.Удалить(\|Движения\." \
  src/cf/Reports/ || echo "OK: отчёты только читают"
```

Если для проверки нужны данные — вводить их документами (можно программно один раз),
а не генерировать при каждом формировании отчёта.

## 10. Проверка результата

### 10.1 Конфигурация

```bash
bash .agents/skills/1c-config-sync/scripts/apply-config.sh
# ожидаем: Database configuration successfully updated / No errors found
```

Если import упал — в ошибке будет имя XML-файла. Частые причины:

| Ошибка | Причина |
|---|---|
| `Different property and XDTO data item` | неверное имя/значение свойства в `Form.xml` |
| `Document is empty` | двойной BOM или пустой файл |
| `Invalid name of form item command` | `Action`/`CommandName` не совпадает с процедурой/командой |
| `Failed to get exclusive lock` | база занята: закрыть `1cv8`, `ibsrv`, `ibcmd` |

### 10.2 Визуально в веб-клиенте

```bash
bash .agents/skills/1c-web-ui-test/scripts/web-up.sh
# OK: http://localhost:8314/labs/ru_RU/  (PID ...)
```

Дальше браузерными инструментами: открыть раздел → «Отчеты» → нужный отчёт → «Сформировать».
Скриншот требует видимого окна: активировать приложение (`osascript -e 'tell application "OpenCode" to activate'`),
затем `browser.tabs.focus` и `browser.screenshot`.

Обязательное завершение:

```bash
bash .agents/skills/1c-web-ui-test/scripts/web-down.sh
# ibsrv остановлен. Порт 8314 закрыт, база свободна.
```

### 10.3 Что смотреть в форме

- даты в полях и в выводе — `dd.MM.yyyy`;
- переключатели — в одну горизонтальную строку (`ColumnsCount` = число вариантов);
- таблица — видимые линии сетки (обводить каждую ячейку `Новый Линия(...)`);
- заголовки — по центру, шапка и нумерация граф на месте;
- группировка — только при сортировке запроса по полю группы;
- нет пустых/отрицательных значений, если по смыслу их быть не должно.

## 11. Гигиена файлов

- XML и BSL — UTF-8; у BSL и большинства XML один BOM (`\ufeff`), не два.
- Переносы строк — LF. `meta-compile` пишет CRLF: нормализовать.
- Не менять `version="2.21"` на другую без причины.
- Не коммитить `Labs_1s/*.cfl`, `1Cv8Log`, бэкапы — они в `.gitignore`.
- Перед коммитом смотреть `git diff --stat`: бинарная база `Labs_1s/1Cv8.1CD`
  меняется после каждого применения/ввода данных — это нормально, но осознанно.

## 12. Git

```bash
git status --short
git fetch origin
git log --oneline --graph -8
# при необходимости:
git add -A
git commit -m "Кратко: что и зачем"
git push origin <ветка>
```

- Не делать `git pull`/merge при незакоммиченных правках в тех же файлах.
- Не разрешать конфликты в бинарной базе «на глаз»: источник истины — `src/cf`,
  базу можно пересобрать применением конфигурации, но пользовательские данные в ней терять нельзя.
- Если ветка отстала от `master` и есть локальные правки — сначала спросить пользователя.

## 13. Чек-лист перед ответом

- [ ] Изменения внесены в `src/cf`, а не только в базу.
- [ ] `apply-config.sh` прошёл, `CheckConfig` — `No errors found`.
- [ ] Форма/кнопка проверена в веб-клиенте (или явно сказано, почему нет).
- [ ] В отчётах нет записи в базу.
- [ ] `ibsrv`/`1cv8`/`ibcmd` не запущены, порт 8314 закрыт, база свободна.
- [ ] В ответе указано, что именно изменено (файлы/объекты) и как проверено.
- [ ] Если закрывались окна пользователя — это явно упомянуто.

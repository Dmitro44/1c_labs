---
name: 1c-form-build
description: Сборка и правка управляемых форм 1С из JSON DSL компилятором form-compile (проект cc-1c-skills): структура файлов формы, обёртка, модуль, регистрация в объекте, DSL-паттерны (гиперссылки, скрытые страницы, alwaysHorizontal). Использовать при создании/изменении форм справочников и документов, при ошибках «Different property and XDTO data item», «Invalid name of form item command», при правке файлов в src/cf/*/Forms.
---

# Сборка форм 1С из JSON DSL

Формы описываются JSON (примеры — в `build/lab2_forms/*.json` и `build/form_sotrudniki_item.json`), компилируются в XML. Исходник истины — JSON + Module.bsl; XML регенерируется.

## Компиляция

```bash
cd <корень проекта>
python3 cc-1c-skills/.claude/skills/form-compile/scripts/form-compile.py \
  -JsonPath build/<имя>.json \
  -OutputPath "src/cf/<Тип>/<Объект>/Forms/<ФормаИмя>/Ext/Form.xml"
sed -i '' 's/version="2\.17"/version="2.21"/' "src/cf/<Тип>/<Объект>/Forms/<ФормаИмя>/Ext/Form.xml"
```

Аргументы только именованные (`-JsonPath`, `-OutputPath`), позиционные не работают.

## Структура формы на диске

```
src/cf/<Тип>/<Объект>/
├── <Объект>.xml                     # регистрация: <Form>Имя</Form> в ChildObjects + DefaultListForm и т.п.
└── Forms/
    ├── <Имя>.xml                    # обёртка <Form uuid="..."> — создаётся отдельно (uuid4), ОДИН BOM
    └── <Имя>/Ext/Form.xml           # скомпилированная форма
        └── Form/Module.bsl          # модуль формы, руками; UTF-8 c BOM (\ufeff)
```

## Обязательные проверки после компиляции

1. **Регистрация**: form-compile сам вставляет `<Form>Имя</Form>` в объект, но иногда НЕ ТУДА — внутрь `<TabularSection>/<ChildObjects>` (глубже уровнем). Проверь `grep -n '<Form>' <Объект>.xml`: запись должна лежать на уровне `\t\t\t<Form>` рядом с остальными формами. Лишнюю перенеси re.sub'ом.
2. **Кодировка**: обёртку и модуль писать с ровно одним BOM (`'\ufeff' + текст`, `encoding='utf-8'`). Двойной BOM = «Document is empty» при import.
3. **Action команд** = точное имя процедуры в Module.bsl. Если процедура `ДобавитьСтажОбработка`, то и `"action": "ДобавитьСтажОбработка"` — рассинхон даёт молча неработающие кнопки.

## DSL-паттерны, проверенные на 8.5

- Кнопки в командную панель ФОРМЫ: `{ "autoCmdBar": "ФормаКоманднаяПанель", "children": [...] }` — только ВНУТРИ `elements` (первым элементом), верхнеуровневой ключ не связывается.
- Кнопка-гиперссылка: `{ "button": "Имя", "type": "hyperlink", "command": "Команда", "title": "..." }`.
- Скрытые страницы (навигация гиперссылками): `{ "pages": "Страницы", "pagesRepresentation": "None", ... }` + в модуле `Элементы.Страницы.ТекущаяСтраница = Элементы.СтраницаХ;`.
- Группы: только `"alwaysHorizontal"` / `"vertical"`. `"horizontalIfPossible"` в веб-клиенте 8.5 СКЛАДЫВАЕТСЯ в столбец (вся форма «лесенкой»).
- Таблица динсписка получает SearchString/ViewStatus/SearchControl автоматически — не описывать руками.
- Стандартные команды сортировки таблиц (`SortListAsc/Desc`) в 8.5 НЕ работают («Invalid name of form item command») — свои команды + `Список.Порядок.Элементы` (см. 1c-platform-quirks про пользовательские настройки).
- `picture` у кнопок/команд в JSON НЕ задавать — XDTO-отказ «Property Picture».
- `pagesRepresentation`: `None` / `TabsOnTop` / `TabsOnBottom` / `TabsOnLeftHorizontal` (закладки слева — как в карточках типовых; именно такое имя значения, НЕ `TabsOnLeft`). Значение можно проверить только прогоном import.

## Применить и проверить

После сборки — `.agents/skills/1c-config-sync/scripts/apply-config.sh`, визуальная проверка — скилл `1c-web-ui-test`. После проверки ОБЯЗАТЕЛЬНО остановить веб-сервер и освободить базу (`1c-web-ui-test/scripts/web-down.sh`) — это обязательный завершающий шаг, см. 1c-web-ui-test и AGENTS.md в корне проекта.

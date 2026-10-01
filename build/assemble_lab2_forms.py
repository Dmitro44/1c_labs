# -*- coding: utf-8 -*-
"""Сборка форм Лабы 2: form-compile -> Ext/Form.xml (+ нормализация версии 2.21),
обёртка Forms/<Имя>.xml, модуль Module.bsl, регистрация <Form> в ChildObjects документа."""
import subprocess
import sys
import uuid as uuidlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "lab2_forms"
FORM_COMPILE = ROOT / "cc-1c-skills" / ".claude" / "skills" / "form-compile" / "scripts" / "form-compile.py"
CF = ROOT / "src" / "cf"

# (json без расширения, объект метаданных, имя формы)
FORMS = [
    ("vvod_forma_dokumenta",          "ВводШтатнойЕдиницы",     "ФормаДокумента"),
    ("vvod_forma_spiska",             "ВводШтатнойЕдиницы",     "ФормаСписка"),
    ("udal_forma_dokumenta",          "УдалениеШтатнойЕдиницы", "ФормаДокумента"),
    ("udal_forma_podbora",            "УдалениеШтатнойЕдиницы", "ФормаПодбора"),
    ("bol_forma_dokumenta",           "Больничные",             "ФормаДокумента"),
    ("priem_forma_dokumenta",         "ПриемНаРаботу",          "ФормаДокумента"),
    ("priem_forma_spiska",            "ПриемНаРаботу",          "ФормаСписка"),
    ("priem_forma_stavok",            "ПриемНаРаботу",          "ФормаПросмотраСтавок"),
    ("priem_forma_zameshchayushchih", "ПриемНаРаботу",          "ФормаПодбораЗамещающих"),
    ("priem_forma_osnovaniy",         "ПриемНаРаботу",          "ФормаПодбораОснований"),
]

OBJECT_MODULES = {
    "ВводШтатнойЕдиницы":     "vvod_ObjectModule.bsl",
    "УдалениеШтатнойЕдиницы": "udal_ObjectModule.bsl",
    "Больничные":             "bol_ObjectModule.bsl",
    "ПриемНаРаботу":          "priem_ObjectModule.bsl",
}

NSDEF = ('xmlns:app="http://v8.1c.ru/8.2/managed-application/core" '
         'xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config" '
         'xmlns:cmi="http://v8.1c.ru/8.2/managed-application/cmi" '
         'xmlns:ent="http://v8.1c.ru/8.1/data/enterprise" '
         'xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform" '
         'xmlns:pal="http://v8.1c.ru/8.1/data/ui/colors/palette" '
         'xmlns:style="http://v8.1c.ru/8.1/data/ui/style" '
         'xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system" '
         'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
         'xmlns:v8ui="http://v8.1c.ru/8.1/data/ui" '
         'xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web" '
         'xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows" '
         'xmlns:xen="http://v8.1c.ru/8.3/xcf/enums" '
         'xmlns:xpr="http://v8.1c.ru/8.3/xcf/predef" '
         'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
         'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')


def wrapper_xml(form_name: str, form_uuid: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" {NSDEF} version="2.21">
\t<Form uuid="{form_uuid}">
\t\t<Properties>
\t\t\t<Name>{form_name}</Name>
\t\t\t<Synonym>
\t\t\t\t<v8:item>
\t\t\t\t\t<v8:lang>ru</v8:lang>
\t\t\t\t\t<v8:content>{form_name}</v8:content>
\t\t\t\t</v8:item>
\t\t\t</Synonym>
\t\t\t<Comment/>
\t\t\t<FormType>Managed</FormType>
\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents>
\t\t\t<UsePurposes>
\t\t\t\t<v8:Value xsi:type="app:ApplicationUsePurpose">PlatformApplication</v8:Value>
\t\t\t\t<v8:Value xsi:type="app:ApplicationUsePurpose">MobilePlatformApplication</v8:Value>
\t\t\t</UsePurposes>
\t\t\t<UseInInterfaceCompatibilityMode>Any</UseInInterfaceCompatibilityMode>
\t\t</Properties>
\t</Form>
</MetaDataObject>"""


def register_in_document(doc: str, form_name: str) -> None:
    import re as _re
    path = CF / "Documents" / f"{doc}.xml"
    s = path.read_text(encoding="utf-8-sig")
    # убрать неверные вложенные регистрации (внутри TabularSection и пр.)
    s = _re.sub(r"^\t+\t<Form>%s</Form>\n" % _re.escape(form_name), "", s, flags=_re.M)
    if f"\t\t\t<Form>{form_name}</Form>" in s:
        return
    marker = "\t\t</ChildObjects>\n\t</Document>"
    assert marker in s, f"ChildObjects не найден в {doc}"
    s = s.replace(marker, f"\t\t\t<Form>{form_name}</Form>\n" + marker, 1)
    path.write_text(s, encoding="utf-8-sig")


def main() -> int:
    failed = 0
    for base, doc, form_name in FORMS:
        print(f"[{doc}.{form_name}]")
        form_dir = CF / "Documents" / doc / "Forms" / form_name
        ext_dir = form_dir / "Ext"
        ext_dir.mkdir(parents=True, exist_ok=True)

        out = ext_dir / "Form.xml"
        r = subprocess.run(
            [sys.executable, str(FORM_COMPILE),
             "-JsonPath", str(BUILD / f"{base}.json"),
             "-OutputPath", str(out)],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout + r.stderr)
            failed += 1
            continue
        print("    скомпилирована: " + str(out.name))

        # нормализация версии формата под платформу 8.5
        xml = out.read_text(encoding="utf-8-sig")
        xml = xml.replace('version="2.17"', 'version="2.21"')
        out.write_text(xml, encoding="utf-8-sig", )

        # модуль формы
        module_src = BUILD / f"{base}.bsl"
        mod_dir = ext_dir / "Form"
        mod_dir.mkdir(exist_ok=True)
        (mod_dir / "Module.bsl").write_text(
            module_src.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")

        # обёртка формы
        (CF / "Documents" / doc / "Forms" / f"{form_name}.xml").write_text(
            wrapper_xml(form_name, str(uuidlib.uuid4())), encoding="utf-8-sig")

        register_in_document(doc, form_name)

    for doc, mod in OBJECT_MODULES.items():
        src = BUILD / mod
        (CF / "Documents" / doc / "Ext" / "ObjectModule.bsl").write_text(
            src.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        print(f"[{doc}] ObjectModule.bsl записан")

    print(f"Готово. Ошибок: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

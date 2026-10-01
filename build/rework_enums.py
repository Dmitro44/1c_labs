# -*- coding: utf-8 -*-
"""Переписывает значения перечислений Лабы 1 под спецификацию Лабы 2.

UUID переименовываемых значений сохраняются (защита ссылок в данных БД),
новые значения получают новые UUID. Порядок значений = порядок спецификации.
"""
import copy
import uuid as uuidlib
from pathlib import Path

from lxml import etree

CF = Path(__file__).resolve().parent.parent / "src" / "cf"
NS = {"md": "http://v8.1c.ru/8.3/MDClasses",
      "v8": "http://v8.1c.ru/8.1/data/core"}

# enum -> список значений в порядке спецификации.
# Кортеж (old_name, new_name, synonym): old_name=None -> новое значение.
TARGETS = {
    "ВидКомплектования": [
        ("ОсновнойШтат", "ТрудовойДоговор", "Трудовой договор"),
        ("Совместительство", "СрочныйТрудовойДоговор", "Срочный трудовой договор"),
        ("ДоговорГПХ", "Контракт", "Контракт"),
    ],
    "ВидРаботы": [
        ("Основная", "Основная", "Основная"),
        ("Внешняя", "Внешнее", "Внешнее совм."),
        ("Внутренняя", "Внутреннее", "Внутреннее совм."),
        ("Совмещение", "Совмещение", "Совмещение"),
    ],
    "ВидПечатиНадбавок": [
        (None, "РазмерСумма", "Размер сумма"),
        ("Размер", "Размер", "Размер"),
        ("Списком", "Сумма", "Сумма"),
    ],
    "ЕдИзм": [
        ("Процент", "Процент", "%"),
        (None, "СтавкаПервогоРазряда", "Ставка первого разряда"),
        ("Рубль", "Сумма", "руб."),
        ("БазоваяВеличина", "БазВеличина", "Баз величина"),
        (None, "ПроцентСтПервогоРазряда", "Процент ст первого разряда"),
        (None, "БазоваяСтавка", "Базовая ставка"),
        (None, "ПроцентБазовойСтавки", "Процент базовой ставки"),
    ],
    "Пол": [
        ("Женский", "Женский", "Женский"),
        ("Мужской", "Мужской", "Мужской"),
    ],
    "СемейноеПоложение": [
        ("НеСостоитВБраке", "Х", "Холост(не замужем)"),
        ("СостоитВБраке", "Ж", "Женат(замужем)"),
        ("РазведенРазведена", "Р", "Разведен(а)"),
        ("ВдовецВдова", "В", "Вдовец(вдова)"),
    ],
    "СтатусСотрудника": [
        ("Работает", "Работает", "Работает"),
        ("ВОтпуске", "Отсутствует", "Отсутствует"),
        ("Уволен", "Уволен", "Уволен"),
    ],
    "СтатусыНадбавок": [
        ("НадбавкаВПроцентеБазовойСтавки", "НадбБазовойСт", "Надбавка в % базовой ставки"),
        (None, "НадбЗаЗвание", "Надбавка за ученое звание"),
        (None, "НадбЗаСтепень", "Надбавка за ученую степень"),
        ("НадбавкаВПроцентеОклада", "НадбавкаОклада", "Надбавка в % оклада"),
    ],
    "ИсточникФинансирования": [
        ("Бюджет", "Бюджет", "Бюджет"),
        ("Внебюджет", "Внебюджет", "Внебюджет"),
    ],
}


def make_value_elem(template: etree._Element, name: str, synonym: str) -> etree._Element:
    el = copy.deepcopy(template)
    el.set("uuid", str(uuidlib.uuid4()))
    props = el.find("md:Properties", NS)
    props.find("md:Name", NS).text = name
    syn = props.find("md:Synonym/v8:item/v8:content", NS)
    syn.text = synonym
    return el


def rework(enum_name: str, values: list) -> None:
    path = CF / "Enums" / f"{enum_name}.xml"
    tree = etree.parse(str(path))
    root = tree.getroot()
    enum = root.find("md:Enum", NS)
    container = enum.find("md:ChildObjects", NS)

    existing = {}
    for v in container.findall("md:EnumValue", NS):
        existing[v.find("md:Properties/md:Name", NS).text] = v
    template = container.findall("md:EnumValue", NS)[0]

    dropped = [n for n in existing if n not in {old for old, _, _ in values if old}]
    for v in container.findall("md:EnumValue", NS):
        container.remove(v)

    for old, new, syn in values:
        if old:
            el = existing[old]
            el.find("md:Properties/md:Name", NS).text = new
            el.find("md:Properties/md:Synonym/v8:item/v8:content", NS).text = syn
        else:
            el = make_value_elem(template, new, syn)
        container.append(el)

    tree.write(str(path), encoding="UTF-8", xml_declaration=True, standalone=True)
    note = f" (+новых: {sum(1 for o, _, _ in values if not o)})"
    print(f"{enum_name}: {len(values)} значений{note}"
          + (f", удалены: {', '.join(dropped)}" if dropped else ""))


for name, vals in TARGETS.items():
    rework(name, vals)
print("Готово.")

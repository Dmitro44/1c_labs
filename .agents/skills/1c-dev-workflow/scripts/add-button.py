#!/usr/bin/env python3
"""Быстро добавить кнопку с командой в управляемую форму 1С.

Пример:
  python3 scripts/add-button.py \
    -Form "src/cf/Documents/ПриемНаРаботу/Forms/ФормаПросмотраСтавок/Ext/Form.xml" \
    -Name ДобавитьСтавки -Title "Добавить ставки…" -Action ДобавитьСтавки \
    -Module "src/cf/Documents/ПриемНаРаботу/Forms/ФормаПросмотраСтавок/Ext/Form/Module.bsl"

Что делает:
  1. находит командную панель (по умолчанию ФормаКоманднаяПанель);
  2. добавляет <Button> с CommandName = Form.Command.<Name>;
  3. добавляет <Command> с Action = <Action> и заголовком <Title>;
  4. при -Module дописывает заготовку &НаКлиенте Процедура <Action>(Команда).
"""

import argparse
import re


def read_text(path):
    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), bom


def write_text(path, text, bom):
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    open(path, "wb").write(data)


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def find_block(text, tag, name):
    """Границы блока <tag name="name"> ... </tag> с учётом вложенности."""
    m = re.search(r'<%s\s+name="%s"' % (re.escape(tag), re.escape(name)), text)
    if not m:
        return None
    start = m.start()
    open_end = text.find(">", m.end()) + 1
    if text[open_end - 2:open_end] == "/>":
        return start, open_end
    depth = 1
    pos = open_end
    pat = re.compile(r"<(/?)%s(?=[\s/>])" % re.escape(tag))
    while depth:
        mm = pat.search(text, pos)
        if not mm:
            raise SystemExit("Не найден закрывающий </%s> для %s" % (tag, name))
        tag_end = text.find(">", mm.end()) + 1
        self_closing = text[tag_end - 2:tag_end] == "/>"
        if mm.group(1) == "/":
            depth -= 1
        elif not self_closing:
            depth += 1
        pos = tag_end
        if depth == 0:
            return start, tag_end
    return start, open_end


def button_xml(indent, name, title, button_id, tip_id, default=False):
    lines = [
        '<Button name="%s" id="%d">' % (name, button_id),
        "\t<Type>CommandBarButton</Type>",
        "\t<CommandName>Form.Command.%s</CommandName>" % name,
        "\t<Title>",
        "\t\t<v8:item>",
        "\t\t\t<v8:lang>ru</v8:lang>",
        "\t\t\t<v8:content>%s</v8:content>" % xml_escape(title),
        "\t\t</v8:item>",
        "\t</Title>",
    ]
    if default:
        lines.append("\t<DefaultButton>true</DefaultButton>")
    lines += [
        '\t<ExtendedTooltip name="%sРасширеннаяПодсказка" id="%d"/>' % (name, tip_id),
        "</Button>",
    ]
    return "".join(indent + line + "\n" for line in lines)


def command_xml(indent, name, title, action, command_id):
    lines = [
        '<Command name="%s" id="%d">' % (name, command_id),
        "\t<Title>",
        "\t\t<v8:item>",
        "\t\t\t<v8:lang>ru</v8:lang>",
        "\t\t\t<v8:content>%s</v8:content>" % xml_escape(title),
        "\t\t</v8:item>",
        "\t</Title>",
        "\t<Action>%s</Action>" % action,
        "</Command>",
    ]
    return "".join(indent + line + "\n" for line in lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-Form", required=True)
    p.add_argument("-Name", required=True)
    p.add_argument("-Title", required=True)
    p.add_argument("-Action", required=True)
    p.add_argument("-To", default="ФормаКоманднаяПанель")
    p.add_argument("-Default", action="store_true", help="сделать кнопку кнопкой по умолчанию")
    p.add_argument("-Module", default=None)
    a = p.parse_args()

    text, bom = read_text(a.Form)

    if re.search(r'<Button\s+name="%s"' % re.escape(a.Name), text):
        raise SystemExit("Кнопка %s уже существует" % a.Name)
    if re.search(r'<Command\s+name="%s"' % re.escape(a.Name), text):
        raise SystemExit("Команда %s уже существует" % a.Name)

    ids = [int(x) for x in re.findall(r'\bid="(\d+)"', text)]
    next_id = max(ids, default=0) + 1
    button_id, tip_id, command_id = next_id, next_id + 1, next_id + 2

    # --- командная панель ---
    bar = find_block(text, "AutoCommandBar", a.To)
    if bar is None:
        m = re.search(r'<AutoCommandBar\s+name="([^"]+)"', text)
        if not m:
            raise SystemExit("В форме нет AutoCommandBar")
        bar = find_block(text, "AutoCommandBar", m.group(1))
    bar_start, bar_end = bar
    bar_text = text[bar_start:bar_end]
    bar_indent = re.search(r"\n([ \t]*)<AutoCommandBar", text[:bar_start])
    bar_indent = bar_indent.group(1) if bar_indent else "\t"

    ci = bar_text.find("<ChildItems>")
    if ci >= 0:
        mm = re.search(r"<ChildItems>\n([ \t]*)<", bar_text)
        child_indent = mm.group(1) if mm else bar_indent + "\t\t"
        close = bar_text.find("</ChildItems>", ci)
        line_start = bar_text.rfind("\n", 0, close) + 1
        insert_at = bar_start + line_start
        text = text[:insert_at] + button_xml(child_indent, a.Name, a.Title,
                                             button_id, tip_id, a.Default) + text[insert_at:]
    else:
        open_end = bar_start + bar_text.find(">") + 1
        block = (bar_indent + "\t<ChildItems>\n"
                 + button_xml(bar_indent + "\t\t", a.Name, a.Title, button_id, tip_id, a.Default)
                 + bar_indent + "\t</ChildItems>\n")
        if bar_text.rstrip().endswith("/>"):
            # <AutoCommandBar .../> -> <AutoCommandBar ...> ... </AutoCommandBar>
            open_tag = bar_text[:bar_text.find(">") + 1]
            new_bar = (open_tag[:-2] + ">\n" + block
                       + bar_indent + "</AutoCommandBar>")
            text = text[:bar_start] + new_bar + text[bar_end:]
        else:
            text = text[:open_end] + "\n" + block + text[open_end:]

    # --- команда ---
    empty_commands = re.search(r"<Commands\s*/>", text)
    commands_end = text.find("</Commands>")
    if empty_commands:
        block = ("<Commands>\n"
                 + command_xml("\t\t", a.Name, a.Title, a.Action, command_id)
                 + "\t</Commands>")
        text = text[:empty_commands.start()] + block + text[empty_commands.end():]
    elif commands_end >= 0:
        mm = re.search(r"<Commands>\n([ \t]*)<", text)
        cmd_indent = mm.group(1) if mm else "\t\t"
        line_start = text.rfind("\n", 0, commands_end) + 1
        text = (text[:line_start]
                + command_xml(cmd_indent, a.Name, a.Title, a.Action, command_id)
                + text[line_start:])
    else:
        form_end = text.rfind("</Form>")
        if form_end < 0:
            raise SystemExit("Не найден </Form>")
        block = ("\t<Commands>\n"
                 + command_xml("\t\t", a.Name, a.Title, a.Action, command_id)
                 + "\t</Commands>\n")
        text = text[:form_end] + block + text[form_end:]

    write_text(a.Form, text, bom)
    print("OK: кнопка %s -> %s (id %d), команда id %d" % (a.Name, a.To, button_id, command_id))

    # --- заготовка обработчика ---
    if a.Module:
        mod, mod_bom = read_text(a.Module)
        if re.search(r"(Процедура|Функция)\s+%s\s*\(" % re.escape(a.Action), mod, re.I):
            print("Обработчик %s уже есть в модуле — не трогаю" % a.Action)
        else:
            stub = (
                "\n&НаКлиенте\nПроцедура %s(Команда)\n\n"
                "\t// TODO: действие кнопки\n\nКонецПроцедуры\n" % a.Action
            )
            area = mod.find("#Область ОбработчикиКомандФормы")
            if area >= 0:
                end = mod.find("#КонецОбласти", area)
                mod = mod[:end] + stub + "\n" + mod[end:]
            else:
                mod = mod.rstrip("\n") + "\n\n" + stub + "\n"
            write_text(a.Module, mod, mod_bom)
            print("OK: заготовка обработчика %s добавлена в модуль" % a.Action)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Перенести элемент управляемой формы 1С в другую группу/страницу/таблицу.

Примеры:
  # посмотреть структуру формы
  python3 scripts/move-element.py -Form <Form.xml> -List

  # перенести поле в другую группу
  python3 scripts/move-element.py -Form <Form.xml> \
    -Element ВидФинансирования -To ГруппаШапка

  # перенести кнопку в начало группы
  python3 scripts/move-element.py -Form <Form.xml> \
    -Element ПроверитьСтавки -To ГруппаДоплаты -Index 0
"""

import argparse
import re
import sys


def read_text(path):
    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), bom


def write_text(path, text, bom):
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    open(path, "wb").write(data)


def find_block(text, name):
    """(tag, start, open_end, end, self_closing) для <tag name="name">."""
    m = re.search(r'<([A-Za-z][\w]*)\s+name="%s"' % re.escape(name), text)
    if not m:
        return None
    tag = m.group(1)
    start = m.start()
    open_end = text.find(">", m.end()) + 1
    if open_end <= 0:
        raise SystemExit("Повреждён тег %s" % name)
    if text[open_end - 2:open_end] == "/>":
        return tag, start, open_end, open_end, True
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
            return tag, start, open_end, tag_end, False
    return tag, start, open_end, open_end, False


def print_tree(text):
    containers = {"Form", "UsualGroup", "Pages", "Page", "Table",
                  "AutoCommandBar", "CommandBar", "ColumnGroup"}
    depth = 0
    pat = re.compile(r"<(/?)" + r"([A-Za-z][\w]*)([^>]*)>")
    for m in pat.finditer(text):
        closing, tag, attrs = m.group(1), m.group(2), m.group(3)
        if closing:
            if tag in containers:
                depth = max(0, depth - 1)
            continue
        self_closing = attrs.rstrip().endswith("/")
        name_m = re.search(r'\bname="([^"]*)"', attrs)
        name = name_m.group(1) if name_m else ""
        if tag in containers or tag in ("Button", "InputField", "LabelField",
                                        "CheckBoxField", "RadioButtonField",
                                        "SpreadsheetDocumentField", "Command"):
            print("  " * depth + tag + (" " + name if name else ""))
        if tag in containers and not self_closing:
            depth += 1


def reindent(block, old_indent, new_indent):
    out = []
    for line in block.split("\n"):
        if line.startswith(old_indent):
            out.append(new_indent + line[len(old_indent):])
        else:
            out.append(line)
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-Form", required=True)
    p.add_argument("-Element", default=None)
    p.add_argument("-To", default=None)
    p.add_argument("-Index", type=int, default=None, help="позиция в группе (0 — первым)")
    p.add_argument("-List", action="store_true", help="показать структуру и выйти")
    a = p.parse_args()

    text, bom = read_text(a.Form)

    if a.List:
        print_tree(text)
        return

    if not a.Element or not a.To:
        raise SystemExit("Нужны -Element и -To (или -List)")

    src = find_block(text, a.Element)
    if src is None:
        raise SystemExit("Элемент %s не найден" % a.Element)
    tag, start, open_end, end, self_closing = src

    line_start = text.rfind("\n", 0, start) + 1
    indent_m = re.match(r"[ \t]*", text[line_start:start])
    old_indent = indent_m.group(0) if indent_m else ""
    block = text[line_start:end]
    remove_end = end
    if text[remove_end:remove_end + 1] == "\n":
        remove_end += 1
    text = text[:line_start] + text[remove_end:]

    target = find_block(text, a.To)
    if target is None:
        raise SystemExit("Цель %s не найдена" % a.To)
    ttag, tstart, topen, tend, tself = target

    tline = text.rfind("\n", 0, tstart) + 1
    tm = re.match(r"[ \t]*", text[tline:tstart])
    target_indent = tm.group(0) if tm else "\t"
    tbody = text[tstart:tend]

    ci = tbody.find("<ChildItems")
    if ci >= 0:
        ci_open_end = tbody.find(">", ci) + 1
        ci_self = tbody[ci_open_end - 2:ci_open_end] == "/>"
        if ci_self:
            # <ChildItems/> -> <ChildItems> ... </ChildItems>
            ci_indent_m = re.search(r"\n([ \t]*)<ChildItems", tbody)
            ci_indent = ci_indent_m.group(1) if ci_indent_m else target_indent + "\t"
            child_indent = ci_indent + "\t"
            block = reindent(block, old_indent, child_indent)
            replacement = ("<ChildItems>\n" + block + "\n" + ci_indent + "</ChildItems>")
            abs_start = tstart + ci
            abs_end = tstart + ci_open_end
            text = text[:abs_start] + replacement + text[abs_end:]
        else:
            ci_close = tbody.find("</ChildItems>", ci_open_end)
            if ci_close < 0:
                raise SystemExit("Повреждён ChildItems у %s" % a.To)
            inner = tbody[ci_open_end:ci_close]
            cm = re.search(r"\n([ \t]*)<", inner)
            child_indent = cm.group(1) if cm else target_indent + "\t\t"
            block = reindent(block, old_indent, child_indent)
            insert_rel = tbody.rfind("\n", 0, ci_close) + 1
            if a.Index is not None and a.Index >= 0:
                positions = [m.start() for m in re.finditer(r"\n[ \t]*<", inner)]
                if a.Index < len(positions):
                    insert_rel = ci_open_end + positions[a.Index] + 1
            insert_at = tstart + insert_rel
            text = text[:insert_at] + block + "\n" + text[insert_at:]
    elif tself:
        # цель записана как <Tag .../> — развернуть в парный тег с ChildItems
        child_indent = target_indent + "\t\t"
        block = reindent(block, old_indent, child_indent)
        new_tag = (text[tstart:topen - 2] + ">\n"
                   + target_indent + "\t<ChildItems>\n"
                   + block + "\n"
                   + target_indent + "\t</ChildItems>\n"
                   + target_indent + "</%s>" % ttag)
        text = text[:tstart] + new_tag + text[tend:]
    else:
        # у цели нет ChildItems — вставить перед закрывающим тегом
        child_indent = target_indent + "\t\t"
        block = reindent(block, old_indent, child_indent)
        insert_at = tend - len("</%s>" % ttag)
        add = ("\n" + target_indent + "\t<ChildItems>\n"
               + block + "\n"
               + target_indent + "\t</ChildItems>\n" + target_indent)
        text = text[:insert_at] + add + text[insert_at:]

    write_text(a.Form, text, bom)
    print("OK: %s (%s) -> %s" % (a.Element, tag, a.To))


if __name__ == "__main__":
    main()

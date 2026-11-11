"""One text file for every value of a project - readable by an engineer, the single source for the scripts.

    # comment
    [GROUP]                         group header (names are free; scripts get {GROUP: {NAME: value}})
    NAME = value ; note             value: a number or plain arithmetic (2/3, 2*4000+1000); everything after ';' is a note
    [SET name]                      a value set: overrides applied on request (what-if variants)
    NAME = value ; note

  read(path)                    -> (groups, sets, notes)
  values(path, value_set=None)  -> flat {NAME: value} (with the set's overrides)
  set_value(path, name, value, note=None)   rewrite ONE value in place, keeping the line's layout and its note
                                             (used to pull a value a human changed inside SolidWorks back into the file)
String lists (e.g. material, coating) are kept as tuples for any group named in TEXT_GROUPS."""
import ast
import operator
import os
import re
import time

TEXT_GROUPS = {"PROPS"}
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg}


def number(text):
    """A number or a plain arithmetic expression; nothing else is evaluated."""
    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError(f"not a number: {text!r}")
    return ev(ast.parse(text.strip(), mode="eval").body)


def read(path):
    groups, sets, notes, cur, in_set = {}, {}, {}, None, False
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            in_set = name.startswith("SET ")
            cur = sets.setdefault(name[4:].strip(), {}) if in_set else groups.setdefault(name, {})
            cur_name = name
            continue
        if "=" not in line or cur is None:
            raise ValueError(f"{os.path.basename(path)} line {n}: expected NAME = value ; note")
        key, rest = line.split("=", 1)
        val, _, note = rest.partition(";")
        key = key.strip()
        cur[key] = tuple(s.strip() for s in val.split(",")) if (not in_set and cur_name in TEXT_GROUPS) else number(val)
        if note.strip() and not in_set:
            notes.setdefault(key, note.strip())
    return groups, sets, notes


def values(path, value_set=None):
    groups, sets, _ = read(path)
    out = {}
    for g, vals in groups.items():
        if g not in TEXT_GROUPS:
            out.update(vals)
    if value_set:
        if value_set not in sets:
            raise ValueError(f"no [SET {value_set}] in {os.path.basename(path)} (have: {', '.join(sets) or 'none'})")
        for k, v in sets[value_set].items():
            if k not in out:
                raise ValueError(f"[SET {value_set}]: unknown name {k}")
            out[k] = v
    return out


def set_value(path, name, value, note=None):
    """Rewrite the value of `name` (first definition outside the sets). The old value goes into the note:
    '... | <note or "changed"> <date>: <old> -> <new>'. Returns the old value text."""
    lines = open(path, encoding="utf-8").read().split("\n")
    in_set = False
    pat = re.compile(rf"^(\s*{re.escape(name)}\s*=\s*)([^;]*?)(\s*)(;.*)?$")
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            in_set = s[1:-1].strip().startswith("SET ")
            continue
        m = pat.match(line) if not in_set else None
        if m:
            old = m.group(2).strip()
            new = f"{value:g}" if isinstance(value, (int, float)) else str(value)
            pad = max(1, len(m.group(2)) + len(m.group(3)) - len(new))
            tail = (m.group(4) or ";").rstrip()
            tail += f" | {note or 'changed'} {time.strftime('%d/%m/%Y')}: {old} -> {new}"
            lines[i] = f"{m.group(1)}{new}{' ' * pad}{tail}"
            open(path, "w", encoding="utf-8").write("\n".join(lines))
            return old
    raise KeyError(f"{name} not found in {os.path.basename(path)}")


def self_test():
    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "params.txt")
    open(p, "w", encoding="utf-8").write(
        "# test\n[GRID]\nSPAN_X          = 12000      ; [D] client\nV_LOW = 2/3 ; ratio\n[PROPS]\nSTEEL = S235, Z275 ; x\n"
        "[SET S15]\nSPAN_X = 15000 ; wider\n")
    g, s, n = read(p)
    assert g["GRID"]["SPAN_X"] == 12000 and abs(g["GRID"]["V_LOW"] - 2 / 3) < 1e-12 and g["PROPS"]["STEEL"] == ("S235", "Z275")
    assert values(p)["SPAN_X"] == 12000 and values(p, "S15")["SPAN_X"] == 15000 and n["SPAN_X"] == "[D] client"
    assert set_value(p, "SPAN_X", 12500.0, "from SolidWorks") == "12000"
    assert values(p)["SPAN_X"] == 12500 and values(p, "S15")["SPAN_X"] == 15000
    line = [l for l in open(p, encoding="utf-8").read().split("\n") if l.startswith("SPAN_X")][0]
    assert "[D] client | from SolidWorks" in line and "12000 -> 12500" in line, line
    print("PARAMFILE TEST OK")


if __name__ == "__main__":
    self_test()

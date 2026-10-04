"""Apply label-set patch files (JSONL) to taxonomy/health-v8.md.

Ops (one JSON object per line):
  {"op": "change", "id": "<full label id>", "row": "| slug | name | definition | examples |[ home |]"}
  {"op": "add", "under": "<topic parent id | narrative family id | frame | evidence | population>", "row": "..."}
  {"op": "remove", "id": "<full label id>"}
  {"op": "parent", "id": "topic:<parent>", "definition": "<new definition paragraph>", "name": "<optional new name>"}

Usage: apply_patches.py SOURCE.md OUT.md patches/*.jsonl
Prints conflicts (two ops on one id) and refuses to apply if any exist,
unless --resolved FILE lists the accepted op per conflicting id.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HEADING_ID = re.compile(r"`([a-z0-9_]+)`\s*$")


def load_ops(paths):
    ops = []
    for path in paths:
        for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            op = json.loads(line)
            op["_src"] = f"{Path(path).name}:{n}"
            ops.append(op)
    return ops


def slug_of(row):
    return row.strip().strip("|").split("|")[0].strip().strip("`* ")


def index(lines):
    """Map label id -> line index of its row; parent id -> heading line; containers -> last table row."""
    rows, parents, containers = {}, {}, {}
    axis = None
    parent = family = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            title = line[3:].strip().lower()
            axis = title.split(" axis")[0] if title.endswith("axis") else None
            parent = family = None
            continue
        if axis == "topic" and line.startswith("#### "):
            m = HEADING_ID.search(line)
            parent = f"topic:{m.group(1)}"
            parents[parent] = i
            containers[parent] = i
            continue
        if axis == "narrative" and line.startswith("### "):
            m = HEADING_ID.search(line)
            family = m.group(1)
            containers[family] = i
            continue
        if axis and line.lstrip().startswith("|"):
            slug = slug_of(line)
            if not slug or set(slug) <= set("-: ") or slug in ("id",):
                if axis in ("frame", "evidence", "population"):
                    containers.setdefault(axis, i)
                continue
            if axis == "topic" and parent:
                rows[f"{parent}.{slug}"] = i
                containers[parent] = i
            elif axis == "narrative" and family:
                rows[f"narrative:{slug}"] = i
                containers[family] = i
            elif axis in ("frame", "evidence", "population"):
                rows[f"{axis}:{slug}"] = i
                containers[axis] = i
    return rows, parents, containers


def main():
    args = sys.argv[1:]
    resolved = {}
    if "--resolved" in args:
        k = args.index("--resolved")
        resolved = {json.loads(l)["id"]: json.loads(l) for l in Path(args[k + 1]).read_text().splitlines() if l.strip()}
        del args[k : k + 2]
    source, out, *patches = args
    ops = load_ops(patches)
    by_id = defaultdict(list)
    for op in ops:
        key = op.get("id") or f"add:{op['under']}:{slug_of(op['row'])}"
        by_id[key].append(op)
    conflicts = {k: v for k, v in by_id.items() if len(v) > 1 and k not in resolved}
    if conflicts:
        for k, v in conflicts.items():
            print(f"CONFLICT {k}: " + " ; ".join(o["_src"] + " " + o["op"] for o in v))
        sys.exit(2)
    final = [resolved[k] if k in resolved else v[0] for k, v in by_id.items()]
    lines = Path(source).read_text(encoding="utf-8").splitlines()
    rows, parents, containers = index(lines)
    problems = []
    replace, delete, insert_after, parent_defs = {}, set(), defaultdict(list), {}
    for op in final:
        kind = op["op"]
        if kind == "change":
            if op["id"] not in rows:
                problems.append(f"change: unknown id {op['id']} ({op['_src']})")
                continue
            if slug_of(op["row"]) != op["id"].split(":", 1)[1].split(".")[-1]:
                problems.append(f"change: row slug {slug_of(op['row'])} != id {op['id']} ({op['_src']})")
                continue
            replace[rows[op["id"]]] = op["row"].strip()
        elif kind == "remove":
            if op["id"] not in rows:
                problems.append(f"remove: unknown id {op['id']} ({op['_src']})")
                continue
            delete.add(rows[op["id"]])
        elif kind == "add":
            under = op["under"]
            if under not in containers:
                problems.append(f"add: unknown container {under} ({op['_src']})")
                continue
            insert_after[containers[under]].append(op["row"].strip())
        elif kind == "parent":
            if op["id"] not in parents:
                problems.append(f"parent: unknown {op['id']} ({op['_src']})")
                continue
            parent_defs[parents[op["id"]]] = op
        else:
            problems.append(f"unknown op {kind} ({op['_src']})")
    if problems:
        print("\n".join(problems))
        sys.exit(3)
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i in parent_defs:
            op = parent_defs[i]
            if op.get("name"):
                m = HEADING_ID.search(line)
                line = f"#### {op['name']} `{m.group(1)}`"
            out_lines.append(line)
            # skip the old definition paragraph (non-empty, non-table lines)
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].lstrip().startswith("|") and not lines[j].startswith("#"):
                j += 1
            out_lines.append(op["definition"].strip())
            if i in insert_after:  # parent with no table rows yet
                out_lines.extend(insert_after[i])
            i = j
            continue
        if i not in delete:
            out_lines.append(replace.get(i, line))
        if i in insert_after:
            if line.startswith("#"):
                # empty container: emit a table header first
                problems.append(f"add into empty container at line {i+1}; add header manually")
            out_lines.extend(insert_after[i])
        i += 1
    if problems:
        print("\n".join(problems))
        sys.exit(3)
    Path(out).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    counts = defaultdict(int)
    for op in final:
        counts[op["op"]] += 1
    print("applied", dict(counts))


if __name__ == "__main__":
    main()

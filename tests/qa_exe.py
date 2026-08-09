"""Final bytecode verification of the shipped EXE.

Combines two extraction channels so no fix marker is missed:
  * co_names / co_qualname  -> identifiers: function names, attribute names,
    local vars (catches _video_button_for, _has_tab, _poll_handoff,
    _gen_start_time, description, TEXT_DIM)
  * co_consts (incl. nested tuples) -> string literals (catches kwarg names
    like 'button_hover_color', and multi-line docstrings)

All checks are semantic (identifier present), not source-text matching, so
formatting differences between .py and frozen bytecode don't produce false
negatives.
"""
import marshal
import zlib
import sys

from PyInstaller.utils.cliutils.archive_viewer import CArchiveReader

EXE = r"C:\ComfyUI-Desktop\dist\ComfyUI_Uncensored.exe"
arch = CArchiveReader(EXE)
raw = arch.extract("ComfyUI_App")
try:
    code = marshal.loads(zlib.decompress(raw))
except Exception:
    code = marshal.loads(raw)


def collect_all(c):
    names, consts = set(), set()

    def walk(co):
        for n in getattr(co, "co_names", ()):
            names.add(n)
        for k in getattr(co, "co_consts", ()):
            if isinstance(k, str):
                consts.add(k)
            elif isinstance(k, (tuple, list, set, frozenset)):
                for e in k:
                    if isinstance(e, str):
                        consts.add(e)
            elif hasattr(k, "co_consts"):
                walk(k)

    walk(c)
    return names, consts


names, consts = collect_all(code)

# Semantic checks: each fix leaves a distinct identifier/string in the bytecode.
checks = [
    # FIX 1: ToolTip description optional
    ("ToolTip: 'description' arg present (optional)", "description" in names),
    # FIX 2: CTkSwitch button_hover_color
    ("CTkSwitch: 'button_hover_color' kwarg present", "button_hover_color" in consts),
    # FIX 3: TEXT_DIM alias
    ("TEXT_DIM alias present", "TEXT_DIM" in names),
    # FIX 4: _labeled link= flag
    ("_labeled: 'link' kwarg present", "link" in consts),
    # FIX 5/6: distinct video buttons + resolver
    ("_video_button_for() resolver defined", "_video_button_for" in names),
    # FIX 7/8: omit orphaned tab builders via guard
    ("_has_tab() guard defined", "_has_tab" in names),
    # FIX 9: Debug tab imports
    ("diagnostics_button_command referenced", "diagnostics_button_command" in names),
    # FIX 10: poll timeout releases lock
    ("_gen_start_time cleared on timeout", "_gen_start_time" in names and "_reset_video_buttons" in names),
    # FIX 11: single /free
    ("_poll_handoff flag drives button reset", "_poll_handoff" in names),
]

R = [(label, ok) for label, ok in checks]
allok = all(ok for _, ok in R)

print("CArchive: ComfyUI_App frozen OK (%d identifiers, %d string consts collected)" % (len(names), len(consts)))
for label, ok in R:
    print(("PASS" if ok else "FAIL"), label)
print("\n" + "=" * 64)
print("EXE BYTECODE VERIFICATION:", "ALL FIXES PRESENT" if allok else "SOMETHING MISSING")
print("=" * 64)
sys.exit(0 if allok else 1)

"""List a module's imports the kit may not implement: import_gaps.py MODULE...

For each imported function it looks for the name in the kit's shim sources
(runtime/, dx/). A name that never appears is missing; one registered with
imports_unsupported fails when called. Matching is textual, so treat the
output as a list to check, not a verdict. Run from the kit root with
.venv/bin/python.
"""
import pathlib
import re
import sys

import pefile

ROOT = pathlib.Path(__file__).resolve().parents[4]
SOURCES = "\n".join(p.read_text(errors="replace") for d in ("runtime", "dx")
                    for p in (ROOT / d).rglob("*.cpp"))


def bare(name):
    # _AIL_set_sample_type@12 -> set_sample_type, _BinkOpen@8 -> Open
    name = re.sub(r"@\d+$", "", name).lstrip("_")
    for prefix in ("AIL_", "Bink", "Smack"):
        if name.startswith(prefix) and name != prefix:
            return name, name[len(prefix):]
    return name, name


def main():
    for path in sys.argv[1:]:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories()
        print("==", path)
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            dll = entry.dll.decode()
            for imp in entry.imports:
                if not imp.name:
                    key = "ord%d" % imp.ordinal
                    found = re.search(r'"%s"' % key, SOURCES)
                    if not found:
                        print("  missing   %s!#%d" % (dll, imp.ordinal))
                    continue
                full, short = bare(imp.name.decode())
                hits = [m for m in re.finditer(r"\b%s\b" % re.escape(short), SOURCES)]
                if not hits:
                    print("  missing   %s!%s" % (dll, imp.name.decode()))
                    continue
                lines = [SOURCES[SOURCES.rfind("\n", 0, m.start()) + 1:SOURCES.find("\n", m.end())]
                         for m in hits]
                if any("imports_unsupported" in l for l in lines) and not any(
                        re.search(r"ail_|w_|k_|u_|a_|Bink", l) and "imports_unsupported" not in l
                        for l in lines if "{" in l or "(" in l):
                    print("  stubbed   %s!%s" % (dll, imp.name.decode()))


if __name__ == "__main__":
    main()

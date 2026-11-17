"""Find code references in a PE: xrefs.py IMAGE TARGET [--window N]

TARGET is a string (its address is searched as an immediate), a hex address
(searched as an immediate, a call/jmp target and an import-slot call), or
DLL!Function for every call through that import slot. Each hit is
disassembled with N bytes of context either side. Uses the image's own
base; analyse a rebased copy for an auxiliary module.
"""
import argparse
import re
import struct

import capstone
import pefile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("target")
    ap.add_argument("--window", type=lambda v: int(v, 0), default=0x30)
    a = ap.parse_args()
    pe = pefile.PE(a.image)
    img = pe.get_memory_mapped_image()
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    iat = {}
    for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        for i in e.imports:
            iat[i.address] = "%s!%s" % (e.dll.decode(), (i.name or b"#%d" % i.ordinal).decode())

    targets = []
    if "!" in a.target:
        targets = [addr for addr, name in iat.items() if name.lower() == a.target.lower()]
    elif re.fullmatch(r"0x[0-9a-fA-F]+", a.target):
        targets = [int(a.target, 16)]
    else:
        targets = [base + m.start() for m in re.finditer(re.escape(a.target.encode() + b"\0"), img)]
    if not targets:
        raise SystemExit("target not found")

    def note(op):
        out = ""
        for tok in re.findall(r"0x[0-9a-f]{5,8}", op):
            v = int(tok, 16)
            if v in iat:
                out += " ; " + iat[v]
            elif base <= v < base + len(img):
                o = v - base
                end = img.find(b"\0", o, o + 64)
                text = img[o:end] if end > o else b""
                if len(text) > 2 and text.isascii() and text.decode().isprintable():
                    out += " ; %r" % text.decode()
        return out

    sites = set()
    for t in targets:
        packed = struct.pack("<I", t)
        sites.update(base + m.start() for m in re.finditer(re.escape(packed), img))
        for sec in pe.sections:
            if not sec.Characteristics & 0x20000000:
                continue
            code = img[sec.VirtualAddress:sec.VirtualAddress + sec.Misc_VirtualSize]
            for i in range(len(code) - 5):
                if code[i] in (0xE8, 0xE9):
                    at = base + sec.VirtualAddress + i
                    if at + 5 + struct.unpack("<i", code[i + 1:i + 5])[0] == t:
                        sites.add(at)
    for site in sorted(sites):
        print("== %#x" % site)
        start = site - a.window
        for ins in md.disasm(img[start - base:site - base + a.window], start):
            mark = ">>" if ins.address <= site < ins.address + ins.size else "  "
            print("%s %x: %s %s%s" % (mark, ins.address, ins.mnemonic, ins.op_str, note(ins.op_str)))


if __name__ == "__main__":
    main()

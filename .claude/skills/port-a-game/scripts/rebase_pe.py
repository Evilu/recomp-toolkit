"""Rebase a PE image with its relocation table: rebase_pe.py SRC DST 0xBASE.

Auxiliary modules must load at or above GUEST_SHIM_END (0x10000000); analyse
and map the rebased copy, and give game.toml the same base.
"""
import struct
import sys


def rebase(src, dst, new_base):
    data = bytearray(open(src, "rb").read())
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    opt = pe + 24
    old_base = struct.unpack_from("<I", data, opt + 28)[0]
    delta = (new_base - old_base) & 0xFFFFFFFF
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    osz = struct.unpack_from("<H", data, pe + 20)[0]
    sections = []
    for i in range(nsec):
        s = opt + osz + i * 40
        vs, va, rs, ro = struct.unpack_from("<IIII", data, s + 8)
        sections.append((va, max(vs, rs), ro, rs))

    def off(rva):
        for va, size, ro, rs in sections:
            if va <= rva < va + size and rva - va < rs:
                return ro + rva - va
        return None

    rva, size = struct.unpack_from("<II", data, opt + 96 + 5 * 8)
    if delta and not size:
        raise SystemExit("no relocations")
    pos, end, count = rva, rva + size, 0
    while delta and pos + 8 <= end:
        page, block = struct.unpack_from("<II", data, off(pos))
        if block < 8:
            break
        for slot in range(pos + 8, pos + block, 2):
            entry = struct.unpack_from("<H", data, off(slot))[0]
            if entry >> 12 != 3:
                continue
            at = off(page + (entry & 0xFFF))
            if at is None:
                continue
            value = (struct.unpack_from("<I", data, at)[0] + delta) & 0xFFFFFFFF
            struct.pack_into("<I", data, at, value)
            count += 1
        pos += block
    struct.pack_into("<I", data, opt + 28, new_base)
    open(dst, "wb").write(data)
    print(f"{src}: {old_base:08x} -> {new_base:08x}, {count} relocations")


if __name__ == "__main__":
    rebase(sys.argv[1], sys.argv[2], int(sys.argv[3], 16))

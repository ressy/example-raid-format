#!/usr/bin/env python

"""
Essentially mdadm --examine except for the bitmap stuff.

https://raid.wiki.kernel.org/index.php/RAID_superblock_formats
"""

import sys
import struct

def mdadmpeek(fileobj):
    """Extract Linux RAID superblock information from an open binary file."""
    u32 = lambda: ("num4", struct.unpack("<I", fileobj.read(4))[0])
    bin32 = lambda: ("bin4", struct.unpack("<I", fileobj.read(4))[0])
    bin8 = lambda: ("bin", struct.unpack("B", fileobj.read(1))[0])
    u64 = lambda: ("num8", struct.unpack("<Q", fileobj.read(8))[0])
    sgn32 = lambda: ("sgn", struct.unpack("<i", fileobj.read(4))[0])
    raw = lambda n: ("raw", struct.unpack("<"+str(n)+"B", fileobj.read(n)))
    char = lambda n: ("char", fileobj.read(n))
    magic = u32()
    superblock_start = 0
    offset = 0
    if magic[1] == 0:
        fileobj.read(0x1000 - 4)
        magic = u32()
        superblock_start = 0x1000
        offset = 0x1000
    if magic[1] != 0xa92b4efc:
        raise Warning(
            "magic number mismatch (%s != %s) is this a version 1.1 or 1.2 superblock?" % (
                hex(magic[1]), "0xa92b4efc"))
    metadata = {}
    metadata['Superblock/"Magic-Number" Identification area'] = {
        "magic": magic,
        "major_version": u32(),
        "feature_map": bin32(),
        "pad0": raw(4)}
    metadata['Per-Array Identification & Configuration area'] = {
        "set_uuid": raw(16),
        "set_name": char(32),
        "ctime": u64(),
        "level": u32(),
        "layout": u32(),
        "size": u64(),
        "chunksize": u32(),
        "raid_disks": u32(),
        # Docs say "# of sectors after superblock that bitmap starts" but I
        # think it's read as number of sectors from the START of the
        # superblock, not the end.
        "bitmap_offset": sgn32()}
    metadata['RAID-Reshape In-Process Metadata Storage/Recovery area'] = {
        "new_level": u32(),
        "reshape_position": u64(),
        "delta_disks": u32(),
        "new_layout": u32(),
        "new_chunk": u32(),
        "pad1": raw(4)}
    metadata['This-Component-Device Information area'] = {
        "data_offset": u64(),
        "data_size": u64(),
        "super_offset": u64(),
        "recovery_offset": u64(),
        "dev_number": u32(),
        "cnt_corrected_read": u32(),
        "device_uuid": raw(16),
        "devflags": bin8(),
        "pad2": raw(7)}
    metadata['Array-State Information area'] = {
        "utime": u64(),
        "events": u64(),
        "resync_offset": u64(),
        "sb_csum": u32(),
        "max_dev": u32(),
        "pad3": raw(32)}
    raid_disks = metadata['Per-Array Identification & Configuration area']['raid_disks'][1]
    # "Length: Variable number of bytes (but at least 768 bytes?) 2 Bytes per
    # device in the array, including both spare-devices and faulty-devices"
    metadata['Device-Roles (Positions-in-Array) area'] = {
        "role%d" % num: raw(2) for num in range(raid_disks)}
    remaining = 0x300 - (raid_disks * 2)
    if remaining > 0:
        metadata['Device-Roles (Positions-in-Array) area']['remaining'] = raw(remaining)
    offset += 0x400 + max(0, (raid_disks * 2) - 0x300)
    # That's it for the superblock.  After that comes bitmap and data.
    # bitmap offset in bytes
    bitmap_offset = metadata['Per-Array Identification & Configuration area'][
        "bitmap_offset"][1] * 0x200
    metadata['Bitmap stuff'] = {'total_offset_in_bytes': ("num4", bitmap_offset + superblock_start)}
    #chunksize = metadata['Per-Array Identification & Configuration area']["chunksize"][1]
    #size = metadata['Per-Array Identification & Configuration area']["size"][1]
    #bitmap_size = size / chunksiz#e
    #fileobj.read(bitmap_offset)
    #metadata["Bitmap stuff"] = {"???": raw(bitmap_size)}
    data_offset = metadata['This-Component-Device Information area']["data_offset"][1] * 512
    try:
        fileobj.read(data_offset - offset)
        metadata["Data"] = {"first512bytes": raw(512)}
    except struct.error:
        pass
    return metadata

def mdadmpeek_report(metadata):
    """Write dictionary of RAID superlock info to stdout."""
    for section, attrs in metadata.items():
        print(section)
        for field, entry in attrs.items():
            if entry[0] == "num4":
                val = "0x" + entry[1].to_bytes(4, "big").hex()
            elif entry[0] == "num8":
                val = "0x" + entry[1].to_bytes(8, "big").hex()
            elif entry[0] == "bin4":
                val = "0b" + "{:032b}".format(entry[1])
            elif entry[0] == "bin":
                val = "0b" + "{:08b}".format(entry[1])
            elif entry[0] == "raw":
                val = "0x" + bytes(entry[1]).hex()
            elif entry[0] == "char":
                val = entry[1]
            else:
                val = entry[1]
            print("  {key:<20} {val}".format(key=field, val=val))

def mdadmpeek_main():
    """Read RAID superblock from stdin and print report to stdout."""
    metadata = mdadmpeek(sys.stdin.buffer)
    mdadmpeek_report(metadata)

if __name__ == "__main__":
    mdadmpeek_main()

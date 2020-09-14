# Linux RAID Metadata Storage Example

While troubeshooting a storage controller card I realized I wasn't quite clear
how and where Linux's software RAID infrastructure stores its metadata about
arrays, and also realized that I should be, in case of a messy recovery.  The
kernel's wiki page about [RAID superblock formats] cleared up the main ideas
(though, there are a number of question marks on that page that somebody should
probably address at some point).

The included Python script parses out the bytes of a version 1.1 or 1.2
superblock that occur near the beginning of a device by reading bytes from a
pipe.  Something like:

    $ sudo cat /dev/sda1 | python parseraid.py

This should be roughly/mostly what you get when using the real mdadm tool:

    $ sudo mdadm --examine /dev/sda1

Takeaways from writing that:

 * All array information (UUID, RAID level, number of devices, etc.) is stored on
   *all* component devices independently.  (Good!)
 * Per-device information is stored on each device after the shared array info.
 * The device number given for each component matches its position in the
   positions-in-array area at the end of the superblock, so each device knows
   where it fits in.
 * The arrangement of devices listed in `mdadm --detail <array>` matches the
   layout and offset given in the metadata.

So in the case of my left-symmetric RAID 6 array, the first block of component
0 is parity, the first block of component 1 contains the beginning of /dev/md0
at the `data_offset` value of 0x40000 blocks in, or 0x40000 * 0x200 = 128MB.  I
can see the XFS magic bytes "XFSB" at the start of the filesystem when reading
from either device.

    $ sudo dd if=/dev/md0 bs=1 count=4 status=none; echo
    XFSB
    $ sudo dd if=/dev/sds1 skip=128M bs=1 count=4 status=none; echo
    XFSB


[RAID superblock formats]: https://raid.wiki.kernel.org/index.php/RAID_superblock_formats

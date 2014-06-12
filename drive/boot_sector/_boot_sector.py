# encoding: utf-8

from construct import *
from ..keys import *
from misc import MAGIC_END_SECTION


def calc_chs_address(key):
    def _(context):
        h, s, c = context[key]

        head = h
        sector = 0b111111 & s
        cylinder = (0b11000000 & s) << 2 | c

        return cylinder, head, sector
    return _


def _partition_entry_template(abs_pos):
    return Struct(k_PartitionEntry,
        # status is not needed so we don't parse this attribute
        Byte(k_status),

        # chs address is useful when locating certain partitions
        Array(3, ULInt8(k_starting_chs_address)),
        # parse them into a 3-tuple now
        Value(k_starting_chs_address,
              calc_chs_address(k_starting_chs_address)),

        Byte(k_partition_type),
        Value(k_partition_type, lambda c: {
            0x0: k_ignored,
            0x5: k_ExtendedPartition,
            0xf: k_ExtendedPartition,
            0xb: k_FAT32,
            0xc: k_FAT32,
            0x7: k_NTFS,
        }[c[k_partition_type]]),

        Array(3, ULInt8(k_ending_chs_address)),
        Value(k_ending_chs_address,
              calc_chs_address(k_ending_chs_address)),

        ULInt32(k_first_sector_address),
        Value(k_first_byte_address, # this is an absolute address
              lambda c: c[k_first_sector_address] * 512 + abs_pos),
        ULInt32(k_number_of_sectors),

        allow_overwrite=True
    )

def boot_sector_template(abs_pos):
    return Struct(k_MBR,
        # bootstrap code is not parsed for its less importance
        Bytes(None, 0x1be),

        # rename PartitionEntry to its plural form
        Rename(k_PartitionEntries,
               Array(4, _partition_entry_template(abs_pos))),

        Magic(MAGIC_END_SECTION)
    )
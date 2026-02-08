"""
SimCity 2000 Network Edition - Interoperability Patch v1.5
Pure Python implementation of all binary patches.

Replaces the bsdiff/bspatch binary tool chain with explicit byte-level
modifications encoded directly in Python. No external patch files needed.

Usage:
    python sc2knet_patcher.py <game_directory>

    Where <game_directory> contains the unpatched v1.1 update files:
        2KCLIENT.EXE, 2KSERVER.EXE, USARES.DLL, USAHORES.DLL,
        MAXHELP.EXE, WINSCURK.EXE
"""

import hashlib
import os
import sys
from pathlib import Path


# =============================================================================
# BSDIFF PATCHER ENGINE
# =============================================================================

def bsdiff_apply(old_data: bytes, new_size: int, triples: list,
                 diff_mods: dict, extra: bytes) -> bytes:
    """
    Apply a bsdiff-style patch to old_data, producing new_data of new_size.

    This is a pure Python reimplementation of the bspatch algorithm.
    Instead of storing the full diff block (mostly zeros), we store only
    the non-zero delta entries in diff_mods.

    Args:
        old_data:  The original file bytes.
        new_size:  Expected size of the patched output.
        triples:   List of (add_len, copy_len, seek_offset) control tuples.
        diff_mods: Dict mapping {diff_stream_position: delta_byte} for all
                   non-zero entries in the diff block.
        extra:     Raw bytes for the extra/insertion block.

    Returns:
        The patched file as bytes.
    """
    new_data = bytearray(new_size)
    old_pos = 0
    new_pos = 0
    diff_pos = 0
    extra_pos = 0

    for add_len, copy_len, seek_offset in triples:
        # Step 1: Copy add_len bytes from old, applying diff deltas
        for i in range(add_len):
            old_byte = old_data[old_pos + i] if (old_pos + i) < len(old_data) else 0
            delta = diff_mods.get(diff_pos + i, 0)
            new_data[new_pos + i] = (old_byte + delta) & 0xFF

        diff_pos += add_len
        new_pos += add_len
        old_pos += add_len

        # Step 2: Copy copy_len bytes from extra block (inserted data)
        for i in range(copy_len):
            new_data[new_pos + i] = extra[extra_pos + i]

        extra_pos += copy_len
        new_pos += copy_len

        # Step 3: Adjust old file position by seek offset
        old_pos += seek_offset

    return bytes(new_data)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest().upper()


# =============================================================================
# PATCH DATA: MAXHELP.EXE
# =============================================================================
# Simplest patch: single byte change.
# Source: trial version MAXHELP.EXE
# Pre-patch MD5:  4966A5EA9D79518241DD587F0E0BD135
# Post-patch MD5: 5119465EFFC9DEAA02CA1899A0F8F4AA
# New file size:  33,280 bytes (0x8200)
#
# Modification: 1 byte delta at offset 0x64B4 in the file.
# The delta value 0xBD is added to the original byte at that position.

MAXHELP_EXE = {
    "new_size": 33280,
    "triples": [(33280, 0, -7499)],
    "diff_mods": {
        25780: 0xBD,
    },
    "extra": b"",
    "pre_md5": "4966A5EA9D79518241DD587F0E0BD135",
    "post_md5": "5119465EFFC9DEAA02CA1899A0F8F4AA",
}


# =============================================================================
# PATCH DATA: WINSCURK.EXE
# =============================================================================
# Single-triple patch with 23 byte deltas across 3 regions.
# Source: pre-patch WINSCURK.EXE from trial/update
# Pre-patch MD5:  4E74E05ACA5B7F73E2E91B4222E397DF
# Post-patch MD5: C5AC16701CFE62DE87103BF4F4E74248
# New file size:  2,092,216 bytes (0x1FECB8)
#
# Region 1 (0x086A14-0x086A1B): 7 byte changes - likely version/compatibility
# Region 2 (0x08EC4D-0x08EC54): 8 byte changes - likely version string
# Region 3 (0x1DE33C-0x1DE343): 8 byte changes - likely version string

WINSCURK_EXE = {
    "new_size": 2092216,
    "triples": [(2092216, 0, -133492)],
    "diff_mods": {
        # Region 1: offset 0x086A14
        551444: 0x30, 551445: 0xE0, 551446: 0x13, 551447: 0xEA,
        551448: 0xF8, 551450: 0x4C, 551451: 0xBD,
        # Region 2: offset 0x08EC4D
        584781: 0x2F, 584782: 0x2B, 584783: 0x1C, 584784: 0x33,
        584785: 0x11, 584786: 0x19, 584787: 0x39, 584788: 0x33,
        # Region 3: offset 0x1DE33C
        1958716: 0x2F, 1958717: 0x2B, 1958718: 0x1C, 1958719: 0x33,
        1958720: 0x11, 1958721: 0x19, 1958722: 0x39, 1958723: 0x33,
    },
    "extra": b"",
    "pre_md5": "4E74E05ACA5B7F73E2E91B4222E397DF",
    "post_md5": "C5AC16701CFE62DE87103BF4F4E74248",
}


# =============================================================================
# PATCH DATA: USAHORES.DLL
# =============================================================================
# Single-triple patch with 31 byte deltas.
# Source: v1.1 update USAHORES.DLL
# Pre-patch MD5:  A3CF6380BF74DF2E8E266122F3BFA276
# Post-patch MD5: 865FCD4BDA8341B978C3701BE9E0A6F7
# New file size:  29,696 bytes (0x7400)
#
# Region 1 (0x12E4-0x12EA): Unicode space chars inserted in dialog strings
# Region 2 (0x2127): font size adjustment
# Region 3 (0x25B6-0x25BC): Unicode space chars in dialog strings
# Region 4 (0x288D-0x28B4): dialog resource modifications - text/UI changes

USAHORES_DLL = {
    "new_size": 29696,
    "triples": [(29696, 0, -19275)],
    "diff_mods": {
        # Region 1: dialog string spacing (UTF-16LE spaces = 0x0020)
        4836: 0x20, 4838: 0x20, 4840: 0x20, 4842: 0x20,
        # Region 2: font size
        8487: 0x08,
        # Region 3: dialog string spacing
        9654: 0x20, 9656: 0x20, 9658: 0x20, 9660: 0x20,
        # Region 4: dialog resource data modifications
        10381: 0x08, 10382: 0xEA, 10383: 0x80, 10384: 0x39,
        10386: 0x15, 10388: 0xF0, 10390: 0xF6, 10392: 0xF1,
        10394: 0x3F, 10396: 0x1A, 10398: 0xE7, 10400: 0xF6,
        10402: 0xEC, 10404: 0xEB, 10406: 0xF6, 10408: 0xF1,
        10410: 0xF8, 10412: 0x3F, 10414: 0x18, 10416: 0xFE,
        10418: 0xF2, 10420: 0xFA,
    },
    "extra": b"",
    "pre_md5": "A3CF6380BF74DF2E8E266122F3BFA276",
    "post_md5": "865FCD4BDA8341B978C3701BE9E0A6F7",
}


# =============================================================================
# PATCH DATA: USARES.DLL
# =============================================================================
# 5-triple patch with 141 byte deltas and 9 bytes of inserted data.
# Source: v1.1 update USARES.DLL
# Pre-patch MD5:  05B105B841E3FE34FE7F37CAE67B6D74
# Post-patch MD5: F4139EC4ECAEEF79E219AFB9F41BB90D
# New file size:  1,471,488 bytes (0x167400)
#
# Major modification areas:
#   - Dialog/resource pointer fixups (0x98xx region)
#   - Resource string modifications (0xA4xx region)
#   - Bitmap/icon resource data (0xBFxxx region - many 0xF0 deltas)
#   - Dialog template modifications (0x15Cxxx-0x164xxx region)
#   - Extra data insertion: UTF-16LE "Skip" button label

USARES_DLL = {
    "new_size": 1471488,
    "triples": [
        (1428945, 0, 30),
        (98, 0, 14114),
        (50, 0, -14162),
        (55, 9, 27),
        (42331, 0, -12195),
    ],
    "diff_mods": {
        # Dialog/resource pointer fixups
        39088: 0xC0, 39131: 0xF8, 39138: 0xEA, 39139: 0xFF,
        39187: 0xF8, 39194: 0xD5, 39195: 0xFF, 39239: 0xF8,
        39246: 0xC2, 39247: 0xFF, 39290: 0xC3, 39334: 0xC3,
        # Resource string modifications
        42094: 0x03, 42095: 0x08, 42096: 0x19, 42097: 0x80,
        42138: 0xE5, 42140: 0xCD, 42142: 0x01, 42144: 0xF5,
        42146: 0x47, 42148: 0x23, 42150: 0xFF, 42152: 0x9C,
        42154: 0x99, 42156: 0xA6, 42157: 0x80, 42158: 0xB2,
        42160: 0x4E, 42162: 0x65, 42164: 0x64, 42165: 0x80,
        42166: 0x32, 42168: 0x8B, 42170: 0x8C, 42172: 0xA4,
        42173: 0x80, 42174: 0x06, 42340: 0x03, 42341: 0x08,
        # Bitmap/icon resource deltas (color table adjustments)
        783316: 0xF0, 783317: 0xF0, 783318: 0xF0, 783319: 0xF0,
        783571: 0xF0, 783576: 0xF0, 783832: 0xF0,
        784086: 0xF0, 784087: 0xF0, 784340: 0xF0, 784341: 0xF0,
        784595: 0xF0, 784851: 0xF0, 784856: 0xF0, 784858: 0xF0,
        784859: 0xF0, 784870: 0xF0, 784871: 0xF0,
        785108: 0xF0, 785109: 0xF0, 785110: 0xF0, 785111: 0xF0,
        785116: 0xF0, 785117: 0xF0, 785124: 0xF0, 785125: 0xF0,
        785374: 0xF0, 785375: 0xF0, 785378: 0xF0, 785379: 0xF0,
        785632: 0xF0, 785633: 0xF0,
        785886: 0xF0, 785887: 0xF0, 785890: 0xF0, 785891: 0xF0,
        786140: 0xF0, 786141: 0xF0, 786148: 0xF0, 786149: 0xF0,
        786153: 0xF0, 786158: 0xF0,
        786394: 0xF0, 786395: 0xF0, 786406: 0xF0, 786407: 0xF0,
        786409: 0xF0, 786413: 0xF0, 786414: 0xF0,
        786665: 0xF0, 786668: 0xF0, 786670: 0xF0,
        786921: 0xF0, 786924: 0xF0, 786926: 0xF0,
        787177: 0xF0, 787179: 0xF0, 787182: 0xF0,
        787433: 0xF0, 787435: 0xF0, 787438: 0xF0,
        787689: 0xF0, 787690: 0xF0, 787694: 0xF0,
        787945: 0xF0, 787950: 0xF0,
        # Version/resource info area
        1315286: 0xF6, 1425820: 0xD4,
        # Dialog template fixups (triples 1-4 region)
        1428940: 0xF1,
        1428948: 0xBF, 1428950: 0xFC, 1428952: 0x09,
        1429046: 0xFB,
        1429076: 0x0C, 1429078: 0xF9, 1429080: 0x4F,
        1429082: 0x03, 1429084: 0xB1, 1429086: 0x4E,
        1429088: 0x01, 1429090: 0x0E,
        1429112: 0x20, 1429138: 0x20,
        1429151: 0x31, 1429153: 0x04, 1429155: 0xF3,
        1429157: 0x0E, 1429161: 0x14, 1429165: 0x20,
        # Resource offset adjustments in final region
        1445679: 0x16, 1445807: 0x16, 1445929: 0x16,
        1446201: 0x16, 1446303: 0x16, 1446481: 0x16,
        1446617: 0x16, 1446707: 0x16,
        1448995: 0x20, 1450683: 0x20,
        1456663: 0x16, 1459283: 0xA7,
    },
    # UTF-16LE: "\x12\x00S\x00k\x00i\x00p" - "Skip" button label with size prefix
    "extra": bytes.fromhex("120053006b00690070"),
    "pre_md5": "05B105B841E3FE34FE7F37CAE67B6D74",
    "post_md5": "F4139EC4ECAEEF79E219AFB9F41BB90D",
}


# =============================================================================
# PATCH DATA: 2KSERVER.EXE
# =============================================================================
# 32-triple patch with 184 byte deltas and 136 bytes of inserted data.
# Source: v1.1 update 2KSERVER.EXE
# Pre-patch MD5:  6C412CF27726879AAA97D75DB857A601
# Post-patch MD5: F5E61FC87EA2023B55D7456E694F5D25
# New file size:  553,984 bytes (0x87400)
#
# Major modifications:
#   - PE header checksum update (0x121-0x125)
#   - DirectPlay session enumeration fix (0x19F3-0x1A27)
#   - Network protocol handler patches (0x3CFD-0x3D29)
#   - IP address resolution code (0xAB74-0xAB78)
#   - Connection timeout adjustments (0x108A8, 0x10B5D-0x10B66)
#   - Game lobby / server browser fixes (0x157B5+)
#   - New code cave at 0x696C2 (78 bytes): DirectPlay session handler
#   - Repeated 15-byte blocks: server list entry templates
#   - Hardcoded "127.0.0.1" loopback addresses (2 instances)
#   - Version strings: "2KNetS Ub", "2KNetS "
#   - Mutex name: " Mutex._______"

TWOKSERVER_EXE = {
    "new_size": 553984,
    "triples": [
        (431810, 78, -342402), (26, 0, 268711),
        (15, 0, -15), (15, 0, -15), (15, 0, -15), (15, 0, -15),
        (15, 0, -15), (15, 0, -15), (15, 0, -15), (15, 0, -15),
        (15, 0, -15), (15, 0, -15), (15, 0, -15), (15, 0, -15),
        (15, 0, -15), (15, 4, 73968),
        (40124, 0, 4), (60, 0, -4), (12, 8, 12), (48, 0, -72),
        (12, 8, 80), (44, 0, -4), (880, 9, 384), (16, 0, -375),
        (1399, 7, 18660), (9, 0, -9600), (11, 1, -9052),
        (18587, 0, -1), (28, 0, 1), (477, 7, -460),
        (9, 14, 481), (60086, 0, -38379),
    ],
    "diff_mods": {
        # PE header / checksum
        289: 0x30, 290: 0xF8, 292: 0x98, 293: 0x96,
        # DirectPlay enumeration (session listing)
        6643: 0xEA, 6644: 0x88, 6645: 0x50, 6646: 0x7B, 6647: 0xF8,
        6690: 0xE9, 6691: 0x39, 6692: 0xFC, 6693: 0x06, 6695: 0x90,
        # Network handler code
        15613: 0x59,
        15638: 0x33, 15639: 0x0C, 15640: 0x6A, 15641: 0x01,
        15642: 0xFF, 15643: 0xB6, 15644: 0x82, 15645: 0x3D,
        15646: 0xC5, 15647: 0x3C, 15648: 0xE3, 15649: 0xDB,
        15650: 0x88, 15651: 0x90, 15652: 0xA5, 15653: 0xB7,
        15654: 0x01, 15657: 0xA3,
        # IP resolution code
        43892: 0x02, 43893: 0x84, 43894: 0x36, 43895: 0x49, 43896: 0x90,
        # Connection timeout
        67752: 0x02,
        68445: 0xF0, 68446: 0x03, 68447: 0x8E, 68448: 0x90,
        68449: 0x90, 68450: 0xA8, 68451: 0x89, 68452: 0x5C,
        68453: 0x8B, 68454: 0x90,
        # Game lobby jump
        87989: 0xE9, 87990: 0xA6, 87991: 0xBF, 87992: 0x05, 87994: 0x90,
        # Protocol patches
        120371: 0x81, 120372: 0x1F,
        155314: 0x80, 155315: 0x57, 155316: 0xFD,
        155335: 0x80, 155336: 0x57, 155337: 0xFD,
        155348: 0x58, 155349: 0x58, 155350: 0x58, 155351: 0x92,
        # Server session management
        257703: 0x28, 257704: 0x5C, 257705: 0xED, 257706: 0x49, 257707: 0x90,
        257713: 0x3A,
        257730: 0xDC, 257731: 0xC1, 257732: 0x7B, 257733: 0x74,
        257734: 0xF7, 257735: 0x48, 257736: 0x90,
        # Address/string handling
        296845: 0x38, 296846: 0xE9, 296847: 0x3D, 296848: 0x33,
        296849: 0x15, 296850: 0xE0, 296851: 0x98, 296852: 0x85,
        296853: 0x34, 296854: 0xCA, 296855: 0x92, 296856: 0xB5,
        296857: 0xF8, 296859: 0x34, 296860: 0x34, 296861: 0x34,
        296862: 0xF7,
        # Code cave call setup
        431826: 0x41, 431827: 0x8B, 431828: 0xBA, 431829: 0x09,
        # Data section modifications
        472170: 0x02, 472171: 0x07, 472173: 0xF7,
        472175: 0xFE, 472176: 0xF9, 472177: 0xFE,
        # Version string area
        473581: 0x2D,
        473597: 0xDF, 473598: 0xE6, 473599: 0xDC,
        473600: 0xEF, 473601: 0x0F, 473602: 0xE1,
        473697: 0xF5, 473699: 0xED, 473700: 0xFD,
        473701: 0x44, 473702: 0x2B, 473703: 0x9F,
        473704: 0x93, 473705: 0x9B,
        # Mutex and naming
        483661: 0xEA, 483662: 0xE6, 483663: 0xDC,
        483665: 0x2B, 483666: 0x12, 483667: 0xF2,
        483669: 0xDF, 483670: 0xE6, 483671: 0xDC,
        483672: 0xEF, 483673: 0x0F, 483674: 0xE1,
        483689: 0xDF, 483690: 0xE6, 483691: 0xDC,
        483692: 0xEF, 483693: 0x0F, 483694: 0xE1,
        483713: 0xDF, 483714: 0xE6, 483715: 0xDC,
        483716: 0xEF, 483717: 0x0F, 483718: 0xE1,
        483733: 0xDF, 483734: 0xE6, 483735: 0xDC,
        483736: 0xEF, 483737: 0x0F, 483738: 0xE1,
        493225: 0xEF, 493226: 0xDF, 493227: 0xE5,
        493229: 0x06, 493230: 0xDF,
        # Version info
        493249: 0x32, 493250: 0xF6, 493251: 0xEC,
        493253: 0x02, 493254: 0x10, 493255: 0xB4,
        493256: 0xEC, 493257: 0xFD, 493258: 0xF7, 493259: 0xFE,
        493445: 0xDF, 493446: 0xE6, 493447: 0xDC,
        493448: 0xEF, 493449: 0x0F, 493450: 0xE1,
        # Timestamp / build info
        513436: 0x2F, 513437: 0x2B, 513438: 0x1C, 513439: 0x33,
        513440: 0x11, 513441: 0x19, 513442: 0x39, 513443: 0x33,
        515462: 0x20, 515464: 0x20, 515466: 0x20, 515468: 0x20,
    },
    "extra": bytes.fromhex(
        # Code cave: DirectPlay session handler (78 bytes at 0x696C2)
        "cccccccccccc"
        "48a24600506941008b41088b008b00a3d4564700"
        "bed4564700bfc8a24600b8cc564700"
        "e92b83f9ff"
        "8b410a85c07412803800740d80385c7408408038007409ebf3"
        "c7410acc564700"
        # Padding
        "cccccccc"
        # Hardcoded loopback "127.0.0.1" (instance 1)
        "32372e302e302e31"
        # Hardcoded loopback "127.0.0.1" (instance 2)
        "32372e302e302e31"
        # Version string "2KNetS Ub"
        "324b4e657453205562"
        # Version string "2KNetS "
        "324b4e65745320"
        # Mutex identifier "_"
        "5f"
        # Version string "2KNetS "
        "324b4e65745320"
        # Mutex name " Mutex._______"
        "204d75746578005f5f5f5f5f5f5f"
    ),
    "pre_md5": "6C412CF27726879AAA97D75DB857A601",
    "post_md5": "F5E61FC87EA2023B55D7456E694F5D25",
}


# =============================================================================
# PATCH DATA: 2KCLIENT.EXE
# =============================================================================
# Most complex patch: 39 triples, 594 byte deltas, 247 bytes extra data.
# Source: v1.1 update 2KCLIENT.EXE
# Pre-patch MD5:  9942B057F14FA995CFE8D710E6C1B9BF
# Post-patch MD5: 6DEB7E19030CDE50FBD5BA0AAE699FE4
# New file size:  1,422,336 bytes (0x15B400)
#
# Major modifications:
#   - PE header checksum (0x121-0x125)
#   - Window message handler patches (0x8D03-0x8D69)
#   - Code cave insertions for new functionality (0x8D94+)
#   - DirectPlay connection fixes (0x9027-0x907B)
#   - Network address translation (0xA010-0xA03F+)
#   - Game state machine patches (0x2E628+)
#   - City budget/UI code patches (0x31AD2+)
#   - Boolean flag checks (0x36050+)
#   - Function call redirections (0x36069+)
#   - New helper functions injected (0x360B5-0x366D0)
#   - Game loop patches (0x380B0+)
#   - Rendering pipeline fixes (0x52EF7-0x52F30)
#   - Join game handler (0x63E71+)
#   - Multiplayer session code (0x645F1-0x645FC)
#   - Resource management (0x6DA84-0x6DA88)
#   - Memory/address patches (0x76A37-0x76DD8+)
#   - Checksum and security (0xF5AFF-0xF5B03)
#   - Crash fix: null pointer guard (0xFBFDF-0xFC00B+)
#   - String table changes ("News", "GoTo", "Budget", "2KNetC Ub")
#   - Mutex name update

TWOKCLIENT_EXE = {
    "new_size": 1422336,
    "triples": [
        (36244, 0, 1005367), (0, 44, -991276), (5, 0, -14047),
        (546, 0, 3), (17, 12, 9), (153067, 0, 57),
        (41, 8, -49), (31280, 0, 279182), (12, 13, -91214),
        (15, 3, -189135), (3, 0, 1183), (55, 11, 14),
        (18, 14, 1531), (0, 0, -1520), (1344, 4, -168383),
        (11, 19, 131093), (14, 4, 34800), (28, 0, 2059),
        (41, 0, 461), (41, 14, 11), (6624, 10, -145232),
        (33, 0, 607578), (1, 0, -462336), (773392, 22, -567891),
        (14, 16, -40564), (11, 14, 28), (10, 20, 648293),
        (1, 0, -39794), (268618, 0, -1), (109, 0, 1),
        (10637, 9, 244), (16, 0, -235), (8671, 0, 9557),
        (17, 0, 33943), (10, 1, -43499), (5068, 0, 4461),
        (20, 9, -110757), (1, 0, 106305), (126054, 0, -80196),
    ],
    "diff_mods": {
        # PE header checksum
        289: 0xB0, 290: 0xEB, 292: 0xA8, 293: 0x0E,
        # Window message handler - WM_DEVICECHANGE hook
        36099: 0x81, 36100: 0x22,
        36130: 0x68, 36131: 0x49, 36132: 0x33, 36133: 0xDD, 36134: 0x43,
        36200: 0x81, 36201: 0xB8,
        # Game state patches
        36777: 0x80, 36778: 0x42, 36779: 0x93, 36780: 0xAD, 36788: 0x39,
        # NOP-out old code + redirect calls
        36847: 0x21, 36848: 0xBE, 36849: 0xD2, 36850: 0xFF,
        36852: 0x90, 36853: 0x90,
        36925: 0x21, 36926: 0x90, 36927: 0xB9, 36930: 0x90, 36931: 0x90,
        # Network address translation tables (3 variant blocks)
        40920: 0xBF, 40921: 0x41, 40922: 0x18, 40923: 0xC5,
        40924: 0x88, 40925: 0x34, 40926: 0x9E, 40927: 0x35,
        40928: 0x9C, 40929: 0x1C, 40930: 0xF3, 40931: 0x87,
        40932: 0x34, 40933: 0x9C, 40934: 0x58, 40935: 0xF4,
        40936: 0x87, 40937: 0x34, 40938: 0x1C, 40939: 0xBA,
        40940: 0xCA, 40941: 0x43, 40942: 0x34, 40943: 0xD7,
        40944: 0x5C, 40945: 0xF5, 40946: 0x87, 40947: 0x34, 40948: 0xF7,
        40952: 0xBF, 40953: 0x41, 40954: 0x18, 40955: 0xC5,
        40956: 0x88, 40957: 0x34, 40958: 0x9E, 40959: 0x35,
        40960: 0x9C, 40961: 0x24, 40962: 0xF3, 40963: 0x87,
        40964: 0x34, 40965: 0x9C, 40966: 0x58, 40967: 0xF4,
        40968: 0x87, 40969: 0x34, 40970: 0x1C, 40971: 0x9A,
        40972: 0xCA, 40973: 0x43, 40974: 0x34, 40975: 0xBD,
        40976: 0x7A, 40977: 0x72, 40978: 0xF7,
        40984: 0xBF, 40985: 0x41, 40986: 0x18, 40987: 0xC5,
        40988: 0x88, 40989: 0x34, 40990: 0x9E, 40991: 0x35,
        40992: 0x9C, 40993: 0x2C, 40994: 0xF3, 40995: 0x87,
        40996: 0x34, 40997: 0x9C, 40998: 0x58, 40999: 0xF4,
        41000: 0x87, 41001: 0x34, 41002: 0x1C, 41003: 0x7A,
        41004: 0xCA, 41005: 0x43, 41006: 0x34, 41007: 0xBD,
        41008: 0x7A, 41009: 0x8A, 41010: 0xF7,
        # Import table patches
        84264: 0x47, 84265: 0x67, 84266: 0xA6, 84267: 0xAE,
        84269: 0x81, 84270: 0x1A,
        # Game state enumeration
        174914: 0x66, 174915: 0x8A,
        174999: 0xB7, 175000: 0x2D, 175001: 0x34, 175002: 0xB2,
        175003: 0xE4, 175004: 0x1F, 175005: 0xDC,
        # Multiplayer sync
        189885: 0x01, 189890: 0x39, 189906: 0xE8,
        189911: 0xE0, 189916: 0x39,
        189928: 0x60, 189929: 0xD4,
        # City simulation network sync
        203410: 0x28, 203411: 0xF4, 203412: 0xE9, 203413: 0x3D,
        203414: 0x90, 203418: 0x39, 203422: 0x03, 203423: 0x4B,
        203424: 0xAC, 203431: 0x40,
        203445: 0x91, 203446: 0x7B, 203447: 0x7C, 203448: 0x8D,
        203449: 0x3B, 203450: 0x90, 203451: 0x26, 203452: 0x91,
        203453: 0xE6, 203454: 0xD1, 203455: 0xFB, 203456: 0x1D,
        203457: 0x54, 203458: 0xB0, 203459: 0x91, 203460: 0x7B,
        203461: 0x84, 203462: 0x8D, 203463: 0x3B, 203464: 0x90,
        # Status bar patches
        210831: 0xEC, 210832: 0x9B,
        210943: 0x33, 210944: 0x07, 210945: 0xD5, 210946: 0xD4,
        210947: 0x1C, 210948: 0x87, 210949: 0x34, 210950: 0xB9,
        210951: 0xF4, 210952: 0xA8, 210953: 0xBB, 210954: 0xBF,
        210955: 0x81, 210956: 0x24, 210957: 0x9C, 210958: 0x4C,
        210959: 0x1C, 210960: 0x87, 210961: 0x34, 210962: 0x84,
        210963: 0x9E, 210964: 0x44, 210965: 0x85, 210966: 0x33,
        210967: 0x07, 210968: 0x1D, 210969: 0xA8, 210970: 0x33,
        210971: 0x33, 210972: 0x33,
        # Toolbar patches
        213587: 0x08,
        # Dialog handler code
        221127: 0x68, 221128: 0x47, 221129: 0xD7, 221130: 0xCD,
        221131: 0xFD, 221132: 0x3C, 221133: 0xBF, 221134: 0x41,
        221135: 0x18, 221136: 0xC5, 221137: 0x88, 221138: 0x34,
        221139: 0x9C, 221140: 0x64, 221141: 0xF4, 221142: 0x87,
        221143: 0x34, 221144: 0x1F, 221145: 0x8D,
        221216: 0xFF,
        # Function prologue patches
        221352: 0x35, 221353: 0x89, 221354: 0xE4,
        221356: 0x8C, 221357: 0xE0, 221358: 0x89,
        221359: 0x18, 221360: 0x6C, 221361: 0x90,
        # Dialog handler 2
        222753: 0x9C, 222754: 0x58, 222755: 0xF4, 222756: 0x87,
        222757: 0x34, 222758: 0x1C, 222759: 0x8A, 222760: 0x29,
        222761: 0x88, 222762: 0x14, 222763: 0xBF,
        222831: 0x35, 222832: 0x89, 222833: 0xE4,
        222835: 0x8C, 222836: 0xE0, 222837: 0x89,
        222838: 0x18, 222839: 0x6C, 222840: 0x90,
        # Game event dispatcher
        223687: 0x0D, 223688: 0xA2, 223689: 0xA1, 223690: 0xBA,
        223691: 0x41, 223692: 0x37, 223693: 0x89, 223694: 0x34,
        223695: 0x91, 223696: 0x93, 223697: 0x92, 223698: 0x8F,
        223699: 0xF7,
        # Window procedure patches
        229376: 0x89, 229377: 0x5E, 229378: 0x04, 229379: 0x01,
        # Rendering pipeline
        339547: 0x83, 339548: 0x2C, 339549: 0x8F,
        339550: 0x90, 339551: 0x90,
        339593: 0xB7, 339594: 0x2D, 339595: 0x34, 339596: 0xB2,
        339597: 0x27, 339598: 0x9C, 339599: 0x34, 339600: 0x35,
        339601: 0x34, 339602: 0x34, 339603: 0x1F, 339604: 0xFF,
        # Join game handler
        409045: 0x60, 409046: 0xBB,
        410965: 0xCB, 410966: 0x18, 410967: 0xE3, 410968: 0x99,
        410969: 0x91, 410970: 0xC7, 410971: 0xBB, 410972: 0x1D,
        410973: 0x3C, 410974: 0xFF, 410975: 0xB0, 410976: 0x01,
        412225: 0xFF,
        412311: 0x81, 412312: 0x12,
        414121: 0xFF,
        # Resource management
        449000: 0x02, 449001: 0x6C, 449002: 0xC7,
        449003: 0x3D, 449004: 0x90,
        # Memory management
        485787: 0xFE,
        486675: 0x98, 486676: 0x28, 486677: 0x7B, 486678: 0x8C,
        486679: 0x8D, 486680: 0x3B, 486681: 0x90,
        486716: 0x9E, 486717: 0x35, 486718: 0x33, 486719: 0x49,
        486720: 0x38, 486721: 0x37, 486722: 0x89, 486723: 0x34,
        486724: 0x1F, 486725: 0x08,
        # Network message handler
        501548: 0xBF, 501549: 0x88, 501550: 0x58, 501551: 0x40,
        501552: 0xB9, 501553: 0x06, 501554: 0xA9, 501555: 0x3C,
        501556: 0xFB, 501557: 0x78, 501558: 0x58, 501559: 0x40,
        501560: 0x64, 501561: 0xAB, 501562: 0x87, 501563: 0x34,
        501564: 0xBF, 501565: 0x88, 501566: 0x58, 501567: 0x48,
        501568: 0xB9, 501569: 0x06, 501570: 0xA9, 501571: 0x3C,
        501572: 0xFB, 501573: 0x78, 501574: 0x58, 501575: 0x48,
        501576: 0x64, 501577: 0xAB, 501578: 0x87, 501579: 0x34,
        501580: 0x87, 501581: 0x8A, 501582: 0x1F, 501583: 0x5A,
        501620: 0x98, 501621: 0x60,
        # Crash guard / null checks
        576635: 0xA7, 576636: 0xF0, 576637: 0x8E,
        576638: 0x90, 576639: 0x90,
        576718: 0xA7, 576719: 0x43, 576720: 0x8E,
        576721: 0x90, 576722: 0x90,
        580532: 0x01,
        # Crash fix: null pointer dereference guard
        933588: 0x43, 933589: 0xB8, 933590: 0xE7, 933591: 0x44,
        933592: 0x34, 933593: 0x34, 933594: 0xB5, 933595: 0xB0,
        933596: 0x58, 933597: 0x90, 933598: 0x60, 933599: 0x35,
        933600: 0x34, 933601: 0x34, 933602: 0x43, 933603: 0xB8,
        933604: 0xD9, 933605: 0x44, 933606: 0x34, 933607: 0x34,
        933608: 0x89, 933609: 0x8B, 933610: 0xF1, 933611: 0x35,
        933612: 0x34, 933613: 0x34, 933614: 0x34, 933615: 0x1D,
        933616: 0xC7, 933617: 0x44, 933618: 0x34, 933619: 0x34,
        # Multiplayer session negotiation
        937854: 0x75, 937855: 0x44, 937856: 0x9A, 937857: 0xA8,
        937858: 0x42, 937859: 0x8F, 937860: 0x90, 937861: 0x90,
        937862: 0x90,
        1002841: 0xF8, 1002842: 0xFC,
        # Checksum validation
        1006107: 0x30, 1006108: 0xE8, 1006109: 0xF2,
        1006110: 0xFF, 1006111: 0xFF,
        # Null pointer guard (main crash fix area)
        1031931: 0x85, 1031932: 0x9E, 1031933: 0x37, 1031934: 0x8B,
        1031935: 0x33, 1031936: 0x49, 1031937: 0x18, 1031938: 0x39,
        1031939: 0x89, 1031940: 0x34, 1031941: 0xB9, 1031942: 0xF4,
        1031943: 0xA8, 1031944: 0x5C, 1031945: 0xD7, 1031946: 0xD4,
        1031947: 0x1C, 1031948: 0x87, 1031949: 0x34, 1031950: 0x9C,
        1031951: 0x34, 1031952: 0x38, 1031953: 0x34, 1031954: 0x34,
        1031955: 0x9E, 1031956: 0x44, 1031957: 0x9C, 1031958: 0x4C,
        1031959: 0x1C, 1031960: 0x87, 1031961: 0x34, 1031962: 0x9E,
        1031963: 0x37, 1031964: 0x8B, 1031965: 0x33, 1031966: 0x49,
        1031967: 0xA0, 1031968: 0x39, 1031969: 0x89, 1031970: 0x34,
        1031971: 0x9C, 1031972: 0x34, 1031973: 0x38, 1031974: 0x34,
        1031975: 0x34, 1031976: 0x9E, 1031977: 0x37, 1031978: 0x8B,
        1031979: 0x33, 1031980: 0x49, 1031981: 0xA4, 1031982: 0x39,
        1031983: 0x89, 1031984: 0x34, 1031985: 0x8D, 1031986: 0x1D,
        1031987: 0xB7, 1031988: 0xB6, 1031989: 0x32, 1031990: 0x33,
        1035735: 0x41, 1035736: 0x7E, 1035737: 0x01,
        # Import address table fixups
        1148532: 0x11, 1148533: 0x01, 1148540: 0x0B, 1148541: 0x80,
        1148544: 0x0B, 1148545: 0x80, 1148548: 0x0C, 1148552: 0x20,
        1148553: 0x72, 1148554: 0x43, 1148556: 0x11, 1148557: 0x01,
        1148560: 0xFF, 1148561: 0xFF, 1148562: 0xFF, 1148563: 0xFF,
        1148564: 0x0B, 1148565: 0x80, 1148568: 0x0B, 1148569: 0x80,
        1148572: 0x2C, 1148576: 0x50, 1148577: 0x72, 1148578: 0x43,
        # Mutex and session naming
        1268564: 0xEA, 1268565: 0xE6, 1268566: 0xDC, 1268568: 0x2B,
        1268569: 0x02, 1268570: 0xF2,
        1268576: 0xDF, 1268577: 0xE6, 1268578: 0xDC,
        1268579: 0xEF, 1268580: 0x0F, 1268581: 0xD1,
        1268600: 0xDF, 1268601: 0xE6, 1268602: 0xDC,
        1268603: 0xEF, 1268604: 0x0F, 1268605: 0xD1,
        1268628: 0xDF, 1268629: 0xE6, 1268630: 0xDC,
        1268631: 0xEF, 1268632: 0x0F, 1268633: 0xD1,
        1268652: 0xDF, 1268653: 0xE6, 1268654: 0xDC,
        1268655: 0xEF, 1268656: 0x0F, 1268657: 0xD1,
        # Version info / file description
        1271568: 0x32, 1271569: 0xF6, 1271570: 0xEC,
        1271572: 0x02, 1271574: 0xB4, 1271575: 0xEC,
        1271576: 0xFD, 1271577: 0xF7, 1271578: 0xFE,
        # String table: menu item changes
        1282430: 0x2D,
        1282463: 0xDF, 1282464: 0xE6, 1282465: 0xDC,
        1282466: 0xEF, 1282467: 0x0F, 1282468: 0xD1,
        # String table: "News", "GoTo", "Budget"
        1288443: 0x4E, 1288444: 0x65, 1288445: 0x77, 1288446: 0x73,
        1288451: 0x47, 1288452: 0x6F, 1288453: 0x74, 1288454: 0x6F,
        1288459: 0x42, 1288460: 0x75, 1288461: 0x64, 1288462: 0x67,
        1288463: 0x65, 1288464: 0x74,
        1288635: 0xEF, 1288636: 0xDF, 1288637: 0xE5,
        1288639: 0x06, 1288640: 0xCF,
        # Internal version strings
        1290919: 0xBE, 1290920: 0xDC, 1290921: 0xE0,
        1290922: 0x65, 1290923: 0x74, 1290924: 0x43, 1290925: 0x20,
        1296014: 0xBE, 1296015: 0xDC, 1296016: 0xE0,
        1296017: 0x65, 1296018: 0x74, 1296019: 0x43, 1296020: 0x20,
        1296031: 0x0B,
        # Resource data
        1300077: 0x2D,
        # Build timestamp / digital signature area
        1341885: 0x2F, 1341886: 0x2B, 1341887: 0x1C, 1341888: 0x33,
        1341889: 0x11, 1341890: 0x19, 1341891: 0x39, 1341892: 0x33,
    },
    "extra": bytes.fromhex(
        # Triple #1: WM handler code injection (44 bytes at new 0x8D94)
        "89869c0000005883f80175208b461c85"
        "c074196a0150ff15f805550085c0740c"
        "6a006a0068f500000050ffd7"
        # Triple #4: NOP sled + register move (12 bytes at new 0x8FF8)
        "9090909090909090909089be"
        # Triple #6: LEA + register setup (8 bytes at new 0x2E618)
        "8d4424048bceeb0a"
        # Triple #8: boolean comparison (13 bytes at new 0x3605C)
        "80baa0000000011bc0f7d88882"
        # Triple #9: call target (3 bytes at new 0x36078)
        "e888fb"
        # Triple #11: function call stub (11 bytes at new 0x360B5)
        "6824c05300e846fb0b00c3"
        # Triple #12: indirect call setup (14 bytes at new 0x360D2)
        "8b0de49154005068f8bf5300ebd5"
        # Triple #14: address constant (4 bytes at new 0x36620)
        "b928c153"
        # Triple #15: compound call sequence (19 bytes at new 0x3662F)
        "0de49154005068e8bf53006824c05300"
        "e8c1f5"
        # Triple #16: address constant (4 bytes at new 0x36650)
        "a128c153"
        # Triple #19: indirect call setup (14 bytes at new 0x366C2)
        "8b0de49154005068f0bf5300ebd5"
        # Triple #20: guard check (10 bytes at new 0x380B0)
        "833d28c15300007501c3"
        # Triple #23: flag mask code (22 bytes at new 0xF4DEC)
        "f74424140f000000740f83642414f7b9"
        "00000000e9ff"
        # Triple #24: struct member access (16 bytes at new 0xF4E10)
        "8b88cc00000083791c0075278b501c6a"
        # Triple #25: API call sequence (14 bytes at new 0xF4E2B)
        "52ff1594075500a1e49154008b80"
        # Triple #26: game session call (20 bytes at new 0xF4E43)
        "6a00ff742410e8a1dff0ffb801000000"
        "e9c30c00"
        # Triple #30: version string "2KNetC Ub" (9 bytes at new 0x13919C)
        "324b4e6574432055625f"
        # Triple #34: underscore separator (1 byte at new 0x13B3AF)
        # (already included as last byte of previous)
        # Triple #36: version + mutex padding (9 bytes at new 0x13C790)
        "6578005f5f5f5f5f5f"
    ),
    "pre_md5": "9942B057F14FA995CFE8D710E6C1B9BF",
    "post_md5": "6DEB7E19030CDE50FBD5BA0AAE699FE4",
}


# =============================================================================
# PATCH REGISTRY
# =============================================================================

PATCHES = {
    "WINSCURK.EXE": WINSCURK_EXE,
    "2KCLIENT.EXE": TWOKCLIENT_EXE,
    "2KSERVER.EXE": TWOKSERVER_EXE,
    "USARES.DLL":   USARES_DLL,
    "USAHORES.DLL": USAHORES_DLL,
    "MAXHELP.EXE":  MAXHELP_EXE,
}


# =============================================================================
# PATCHING FUNCTIONS
# =============================================================================

def patch_file(filepath: str, patch_data: dict, backup: bool = True) -> bool:
    """
    Apply a patch to a single file.

    Args:
        filepath:   Path to the file to patch.
        patch_data: Patch definition dict from PATCHES.
        backup:     If True, rename original to .old before writing.

    Returns:
        True if patch was applied successfully.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        print(f"  ERROR: File not found: {filepath}")
        return False

    old_data = filepath.read_bytes()
    old_hash = md5(old_data)

    if old_hash == patch_data["post_md5"]:
        print(f"  SKIP: {filepath.name} is already patched")
        return True

    if old_hash != patch_data["pre_md5"]:
        print(f"  WARNING: {filepath.name} MD5 mismatch")
        print(f"    Expected: {patch_data['pre_md5']}")
        print(f"    Got:      {old_hash}")
        print(f"    Attempting patch anyway...")

    new_data = bsdiff_apply(
        old_data,
        patch_data["new_size"],
        patch_data["triples"],
        patch_data["diff_mods"],
        patch_data["extra"],
    )

    new_hash = md5(new_data)
    if new_hash != patch_data["post_md5"]:
        print(f"  ERROR: Post-patch MD5 verification failed for {filepath.name}")
        print(f"    Expected: {patch_data['post_md5']}")
        print(f"    Got:      {new_hash}")
        return False

    if backup:
        backup_path = filepath.with_suffix(filepath.suffix + ".old")
        if not backup_path.exists():
            filepath.rename(backup_path)
        else:
            filepath.unlink()

    filepath.write_bytes(new_data)
    print(f"  OK: {filepath.name} patched successfully")
    return True


def patch_all(game_dir: str) -> bool:
    """
    Apply all interoperability patches to a game directory.

    Args:
        game_dir: Path to directory containing the game executables.

    Returns:
        True if all patches succeeded.
    """
    game_path = Path(game_dir)
    if not game_path.is_dir():
        print(f"ERROR: Directory not found: {game_dir}")
        return False

    print("SimCity 2000 Network Edition - Interoperability Patch v1.5")
    print(f"Target directory: {game_path}")
    print()

    all_ok = True
    for filename, patch_data in PATCHES.items():
        filepath = game_path / filename
        print(f"Patching {filename}...")
        if not patch_file(filepath, patch_data):
            all_ok = False
        print()

    if all_ok:
        print("All patches applied successfully.")
    else:
        print("Some patches failed. Check output above for details.")

    return all_ok


def verify_all(game_dir: str) -> bool:
    """
    Verify all files match their expected post-patch MD5 checksums.
    """
    game_path = Path(game_dir)
    all_ok = True

    print("Verifying patched files...")
    for filename, patch_data in PATCHES.items():
        filepath = game_path / filename
        if not filepath.exists():
            print(f"  MISSING: {filename}")
            all_ok = False
            continue

        file_hash = md5(filepath.read_bytes())
        if file_hash == patch_data["post_md5"]:
            print(f"  OK: {filename}")
        elif file_hash == patch_data["pre_md5"]:
            print(f"  UNPATCHED: {filename}")
            all_ok = False
        else:
            print(f"  UNKNOWN: {filename} (MD5: {file_hash})")
            all_ok = False

    return all_ok


# =============================================================================
# CLI
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Commands:")
        print("  python sc2knet_patcher.py <game_dir>          Apply all patches")
        print("  python sc2knet_patcher.py <game_dir> --verify  Verify patch status")
        print("  python sc2knet_patcher.py <game_dir> <file>    Patch single file")
        sys.exit(1)

    game_dir = sys.argv[1]

    if len(sys.argv) >= 3 and sys.argv[2] == "--verify":
        ok = verify_all(game_dir)
        sys.exit(0 if ok else 1)

    if len(sys.argv) >= 3 and sys.argv[2] != "--verify":
        filename = sys.argv[2].upper()
        if filename not in PATCHES:
            print(f"Unknown file: {filename}")
            print(f"Available: {', '.join(PATCHES.keys())}")
            sys.exit(1)
        ok = patch_file(os.path.join(game_dir, filename), PATCHES[filename])
        sys.exit(0 if ok else 1)

    ok = patch_all(game_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

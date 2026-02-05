#!/usr/bin/env python3
"""
is3extract.py - Open source InstallShield 3.x extractor (Pure Python)

Extracts files from InstallShield 3.x self-extracting installers and Z archives.
Handles multiple embedded archives automatically.

No external dependencies - includes pure Python DCL IMPLODE decompressor.

Usage:
  python3 is3extract.py <installer.exe> <output_folder>
  python3 is3extract.py <archive.z> <output_folder>

Options:
  --list          List archives and files without extracting
  --archive N     Extract only archive N (0-based index)

Based on:
  - STIX by Veit Kannegieser
  - blast.c by Mark Adler (DCL decompressor, ported to Python)
"""

import sys
import os
import struct

# InstallShield 3.x signature
IS3_SIGNATURE = b'\x13\x5d\x65\x8c'

# =============================================================================
# DCL IMPLODE Decompressor (Pure Python port of blast.c by Mark Adler)
# =============================================================================

MAXBITS = 13
MAXWIN = 4096

# Huffman code tables (pre-computed from blast.c)
# Literal code lengths (compressed representation)
LITLEN = bytes([
    11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8,
    9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5,
    7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12,
    8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27,
    44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45,
    44, 173
])

# Length code lengths
LENLEN = bytes([2, 35, 36, 53, 38, 23])

# Distance code lengths
DISTLEN = bytes([2, 20, 53, 230, 247, 151, 248])

# Base values for length codes
BASE = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264]

# Extra bits for length codes
EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]


class BitReader:
    """Bit-level reader for compressed data."""

    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.bitbuf = 0
        self.bitcnt = 0

    def bits(self, need):
        """Read 'need' bits from input."""
        val = self.bitbuf

        while self.bitcnt < need:
            if self.pos >= len(self.data):
                raise ValueError("Unexpected end of input")
            val |= self.data[self.pos] << self.bitcnt
            self.pos += 1
            self.bitcnt += 8

        self.bitbuf = val >> need
        self.bitcnt -= need

        return val & ((1 << need) - 1)


class HuffmanTable:
    """Huffman decoding table."""

    def __init__(self, rep):
        """Build table from compressed representation."""
        self.count = [0] * (MAXBITS + 1)
        self.symbol = []

        # Expand compressed lengths
        lengths = []
        for b in rep:
            count = (b >> 4) + 1
            length = b & 15
            lengths.extend([length] * count)

        n = len(lengths)

        # Count codes of each length
        for length in lengths:
            self.count[length] += 1

        # Generate offsets
        offs = [0] * (MAXBITS + 1)
        for i in range(1, MAXBITS):
            offs[i + 1] = offs[i] + self.count[i]

        # Build symbol table
        self.symbol = [0] * n
        for sym, length in enumerate(lengths):
            if length != 0:
                self.symbol[offs[length]] = sym
                offs[length] += 1

    def decode(self, reader):
        """Decode one symbol from the bit stream."""
        code = 0
        first = 0
        index = 0

        for length in range(1, MAXBITS + 1):
            code |= reader.bits(1) ^ 1  # Invert bit
            count = self.count[length]

            if code < first + count:
                return self.symbol[index + (code - first)]

            index += count
            first = (first + count) << 1
            code <<= 1

        raise ValueError("Invalid Huffman code")


def decompress_dcl(data):
    """
    Decompress PKWare DCL IMPLODE data.

    Returns decompressed bytes, or None on error.
    """
    if len(data) < 2:
        return None

    try:
        reader = BitReader(data)
        output = bytearray()
        window = bytearray(MAXWIN)
        window_pos = 0
        first = True

        # Read header
        lit = reader.bits(8)  # 0 = uncoded literals, 1 = coded
        dict_bits = reader.bits(8)  # 4, 5, or 6

        if lit > 1:
            return None
        if dict_bits < 4 or dict_bits > 6:
            return None

        # Build Huffman tables
        litcode = HuffmanTable(LITLEN) if lit else None
        lencode = HuffmanTable(LENLEN)
        distcode = HuffmanTable(DISTLEN)

        # Decompress
        while True:
            if reader.bits(1):  # Length/distance pair
                # Get length
                symbol = lencode.decode(reader)
                length = BASE[symbol] + reader.bits(EXTRA[symbol])

                if length == 519:  # End code
                    break

                # Get distance
                dist_extra = 2 if length == 2 else dict_bits
                dist = distcode.decode(reader) << dist_extra
                dist += reader.bits(dist_extra)
                dist += 1

                if first and dist > window_pos:
                    return None  # Distance too far back

                # Copy from window
                for _ in range(length):
                    # Handle wrap-around in window
                    src_pos = (window_pos - dist) % MAXWIN
                    byte = window[src_pos]

                    output.append(byte)
                    window[window_pos] = byte
                    window_pos = (window_pos + 1) % MAXWIN

                    if window_pos == 0:
                        first = False
            else:
                # Literal byte
                if lit:
                    symbol = litcode.decode(reader)
                else:
                    symbol = reader.bits(8)

                output.append(symbol)
                window[window_pos] = symbol
                window_pos = (window_pos + 1) % MAXWIN

                if window_pos == 0:
                    first = False

        return bytes(output)

    except (ValueError, IndexError) as e:
        return None


# =============================================================================
# InstallShield 3.x Archive Parser
# =============================================================================

def find_is3_archives(data):
    """Find all IS3 archives in the data."""
    archives = []
    pos = 0

    while True:
        pos = data.find(IS3_SIGNATURE, pos)
        if pos == -1:
            break

        if pos + 0x33 <= len(data):
            file_count = struct.unpack('<H', data[pos + 0x0C:pos + 0x0E])[0]
            archive_len = struct.unpack('<L', data[pos + 0x12:pos + 0x16])[0]
            name_offset = struct.unpack('<L', data[pos + 0x29:pos + 0x2D])[0]
            dir_count = struct.unpack('<H', data[pos + 0x31:pos + 0x33])[0]

            archives.append({
                'offset': pos,
                'file_count': file_count,
                'archive_len': archive_len,
                'name_offset': name_offset,
                'dir_count': dir_count,
            })

        pos += 4

    return archives


def parse_file_table(data, archive_info):
    """Parse the file table from an IS3 archive."""
    base = archive_info['offset']
    name_offset = archive_info['name_offset']
    dir_count = archive_info['dir_count']
    file_count = archive_info['file_count']

    files = []
    pos = base + name_offset

    # Parse directory entries - each has a count of files that belong to it
    directories = []
    for i in range(dir_count):
        if pos + 6 > len(data):
            break
        dir_file_count = struct.unpack('<H', data[pos:pos+2])[0]
        block_len = struct.unpack('<H', data[pos+2:pos+4])[0]
        name_len = struct.unpack('<H', data[pos+4:pos+6])[0]
        dir_name = data[pos+6:pos+6+name_len].decode('ascii', errors='ignore').rstrip('\x00')
        directories.append({'name': dir_name, 'file_count': dir_file_count})
        pos += block_len

    # Parse file entries - associate each with its directory
    header_size = 0xFF

    # Build a list that maps file index to directory path
    dir_for_file = []
    for d in directories:
        dir_path = d['name']
        for _ in range(d['file_count']):
            dir_for_file.append(dir_path)

    for i in range(file_count):
        if pos + 0x1E > len(data):
            break

        comp_len = struct.unpack('<L', data[pos+0x07:pos+0x0B])[0]
        file_date = struct.unpack('<H', data[pos+0x0F:pos+0x11])[0]
        file_time = struct.unpack('<H', data[pos+0x11:pos+0x13])[0]
        block_len = struct.unpack('<H', data[pos+0x17:pos+0x19])[0]
        name_len = data[pos+0x1D]
        filename = data[pos+0x1E:pos+0x1E+name_len].decode('ascii', errors='ignore')

        # Get directory for this file
        if i < len(dir_for_file) and dir_for_file[i]:
            full_path = dir_for_file[i] + '\\' + filename
        else:
            full_path = filename

        files.append({
            'name': full_path,
            'compressed_size': comp_len,
            'date': file_date,
            'time': file_time,
        })

        pos += block_len

    # Calculate offsets - files are stored sequentially after header
    current_offset = base + header_size
    for f in files:
        f['compressed_offset'] = current_offset
        current_offset += f['compressed_size']

    return files, directories


def extract_archive(data, archive_info, output_dir, prefix=''):
    """Extract all files from an IS3 archive."""
    files, directories = parse_file_table(data, archive_info)

    os.makedirs(output_dir, exist_ok=True)

    extracted = 0
    failed = 0

    for f in files:
        name = f['name'].replace('\\', '/')
        offset = f['compressed_offset']
        size = f['compressed_size']

        # Create subdirectories if needed
        if '/' in name:
            subdir = os.path.dirname(name)
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)

        print(f"  {prefix}{name}", end='', flush=True)

        # Get compressed data
        comp_data = data[offset:offset + size]

        # Decompress
        decompressed = decompress_dcl(comp_data)

        if decompressed:
            outpath = os.path.join(output_dir, name)
            with open(outpath, 'wb') as out:
                out.write(decompressed)
            print(f" -> {len(decompressed):,} bytes")
            extracted += 1
        else:
            print(" -> FAILED")
            failed += 1

    return extracted, failed


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    list_only = '--list' in sys.argv
    archive_filter = None

    if '--archive' in sys.argv:
        idx = sys.argv.index('--archive')
        if idx + 1 < len(sys.argv):
            archive_filter = int(sys.argv[idx + 1])

    # Read input file
    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    with open(input_file, 'rb') as f:
        data = f.read()

    print(f"Input: {input_file} ({len(data):,} bytes)")

    # Find all IS3 archives
    archives = find_is3_archives(data)

    if not archives:
        print("ERROR: No InstallShield 3.x archives found in file")
        sys.exit(1)

    print(f"Found {len(archives)} archive(s):")

    for i, arch in enumerate(archives):
        print(f"  [{i}] Offset 0x{arch['offset']:x}: {arch['file_count']} files, {arch['archive_len']:,} bytes")

        if list_only:
            files, dirs = parse_file_table(data, arch)
            for d in dirs:
                if d['name']:
                    print(f"       Directory: {d['name']}/")
            for f in files:
                print(f"       - {f['name']} ({f['compressed_size']:,} compressed)")

    if list_only:
        sys.exit(0)

    print()
    print(f"Output: {output_dir}/")
    print()

    # Extract archives
    total_extracted = 0
    total_failed = 0

    for i, arch in enumerate(archives):
        if archive_filter is not None and i != archive_filter:
            continue

        # Use subdirectory if multiple archives
        if len(archives) > 1 and archive_filter is None:
            arch_output = os.path.join(output_dir, f"archive_{i}")
            print(f"Archive [{i}] -> {arch_output}/")
        else:
            arch_output = output_dir
            if len(archives) > 1:
                print(f"Archive [{i}]:")

        extracted, failed = extract_archive(data, arch, arch_output)
        total_extracted += extracted
        total_failed += failed
        print()

    print(f"Done! Extracted {total_extracted} files", end='')
    if total_failed:
        print(f" ({total_failed} failed)")
    else:
        print()


if __name__ == "__main__":
    main()

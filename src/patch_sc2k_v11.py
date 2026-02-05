#!/usr/bin/env python3
"""
SimCity 2000 Network Edition v1.1 Patcher
==========================================
Patches 2KSERVER.EXE and 2KCLIENT.EXE (v1.1) to run on modern Windows (Windows 10/11)

Fixes applied:
- Forces TCP/IP mode (bypasses DirectPlay dependency)
- Removes blocking IPC waits that cause freezes
- Allows multiple client instances
- Shows only "Internet" option in server dialog

Usage (CLI):
    python patch_sc2k_v11.py <path_to_folder_with_v11_files>

Usage (as module):
    from patch_sc2k_v11 import patch_v11

    # Patch binaries in a directory (creates *-v11.EXE files)
    success = patch_v11('/path/to/binaries')

    # Or patch with custom output names
    success = patch_v11('/path/to/binaries', output_suffix='-patched')

    # Patch and replace originals (overwrites!)
    success = patch_v11('/path/to/binaries', output_suffix='', replace=True)
"""

import sys
import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

# =============================================================================
# EXPECTED MD5 CHECKSUMS
# =============================================================================
EXPECTED_MD5 = {
    # Original v1.1 files (unpatched)
    'server_original': '6c412cf27726879aaa97d75db857a601',
    'client_original': '9942b057f14fa995cfe8d710e6c1b9bf',
    # Correctly patched v1.1 files
    'server_patched': '87107cd431db0984681e495952675b9f',
    'client_patched': '64f00668b8caf64cc1757c4a584e7196',
}

# =============================================================================
# V1.1 SERVER PATCHES (2KSERVER.EXE - 553,984 bytes)
# =============================================================================
SERVER_V11_PATCHES = [
    # TCP-only mode patches
    {
        'offset': 0x03ea4,
        'original': bytes([0x74, 0x10]),
        'patched': bytes([0xEB, 0x10]),
        'description': 'Force TCP path in message loop',
        'detail': 'JZ +16 -> JMP +16'
    },
    {
        'offset': 0x116f6,
        'original': bytes([0x0F, 0x84, 0xA3, 0x00, 0x00, 0x00]),
        'patched': bytes([0xE9, 0xA4, 0x00, 0x00, 0x00, 0x90]),
        'description': 'Force TCP path in initialization',
        'detail': 'JZ near -> JMP near'
    },
    {
        'offset': 0x12968,
        'original': bytes([0x0F, 0x84, 0xD0, 0x00, 0x00, 0x00]),
        'patched': bytes([0xE9, 0xD1, 0x00, 0x00, 0x00, 0x90]),
        'description': 'Force TCP path in connection setup',
        'detail': 'JZ near -> JMP near'
    },
    # IPC name scrambling (Server -> Yerver)
    {
        'offset': 0x761c8,
        'original': bytes([0x53]),
        'patched': bytes([0x59]),
        'description': 'Scramble IPC: Server Output Mutex',
        'detail': 'Server -> Yerver'
    },
    {
        'offset': 0x761dc,
        'original': bytes([0x53]),
        'patched': bytes([0x59]),
        'description': 'Scramble IPC: Server Output Semaphore',
        'detail': 'Server -> Yerver'
    },
    {
        'offset': 0x761f4,
        'original': bytes([0x53]),
        'patched': bytes([0x59]),
        'description': 'Scramble IPC: Server Input Mutex',
        'detail': 'Server -> Yerver'
    },
    {
        'offset': 0x76208,
        'original': bytes([0x53]),
        'patched': bytes([0x59]),
        'description': 'Scramble IPC: Server Input Semaphore',
        'detail': 'Server -> Yerver'
    },
    # Wait fixes (INFINITE -> 0ms)
    {
        'offset': 0x00f3b,
        'original': bytes([0x6a, 0xff]),
        'patched': bytes([0x6a, 0x00]),
        'description': 'Fix main loop mutex wait',
        'detail': 'INFINITE -> 0ms'
    },
    {
        'offset': 0x0b660,
        'original': bytes([0x6a, 0xff]),
        'patched': bytes([0x6a, 0x00]),
        'description': 'Fix IT_BLEEDS semaphore wait',
        'detail': 'INFINITE -> 0ms'
    },
    {
        'offset': 0x2010b,
        'original': bytes([0x6a, 0xff]),
        'patched': bytes([0x6a, 0x00]),
        'description': 'Fix Server IPC semaphore wait',
        'detail': 'INFINITE -> 0ms'
    },
    {
        'offset': 0x3ffa0,
        'original': bytes([0x6a, 0xff]),
        'patched': bytes([0x6a, 0x00]),
        'description': 'Fix NEWSPAPER mutex wait',
        'detail': 'INFINITE -> 0ms'
    },
    # Dialog fix: Show only "Internet" option
    {
        'offset': 0x1d609,
        'original': bytes([
            0x56, 0x68, 0x70, 0xe3, 0x41, 0x00, 0xe8, 0x9e,
            0x9e, 0x02, 0x00, 0x6a, 0x00, 0x8b, 0x46, 0x78,
            0x6a, 0x00, 0x8b, 0x3d, 0xf4, 0x9a, 0x48, 0x00
        ]),
        'patched': bytes([
            0x8b, 0x46, 0x78,                    # mov eax, [esi+78h]
            0x68, 0x05, 0x54, 0x47, 0x00,        # push 0x475405 "Internet"
            0x6a, 0x00,                          # push 0
            0x68, 0x80, 0x01, 0x00, 0x00,        # push 0x180 LB_ADDSTRING
            0x50,                                # push eax
            0xff, 0x15, 0xf4, 0x9a, 0x48, 0x00,  # call [SendMessageA]
            0xeb, 0x7f                           # jmp +127 to selection
        ]),
        'description': 'Show only "Internet" in dialog',
        'detail': 'Skip DirectPlay enumeration'
    },
    # Write "Internet" string to data section
    {
        'offset': 0x73805,
        'original': bytes([0x00] * 9),
        'patched': b'Internet\x00',
        'description': 'Add "Internet" string',
        'detail': 'Data section at VA 0x475405'
    },
]

# =============================================================================
# V1.1 CLIENT PATCHES (2KCLIENT.EXE - 1,422,336 bytes)
# =============================================================================
CLIENT_V11_PATCHES = [
    # Singleton bypass - Server Process Mutex check 1
    {
        'offset': 0x3487c,
        'original': bytes([0x74, 0x39]),
        'patched': bytes([0xEB, 0x39]),
        'description': 'Skip Server Process Mutex check 1',
        'detail': 'JE -> JMP'
    },
    # Singleton bypass - Server Process Mutex check 2
    {
        'offset': 0x387c0,
        'original': bytes([0x74, 0x41]),
        'patched': bytes([0xEB, 0x41]),
        'description': 'Skip Server Process Mutex check 2',
        'detail': 'JE -> JMP'
    },
    # Singleton bypass - Client Singleton Mutex check
    {
        'offset': 0x64612,
        'original': bytes([0x0F, 0x85, 0x8B, 0x00, 0x00, 0x00]),
        'patched': bytes([0xE9, 0x8C, 0x00, 0x00, 0x00, 0x90]),
        'description': 'Allow multiple client instances',
        'detail': 'JNE near -> JMP near'
    },
    # IPC name scrambling (Server -> Xerver)
    {
        'offset': 0x135c44,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Output Mutex',
        'detail': 'Server -> Xerver'
    },
    {
        'offset': 0x135c5c,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Output Semaphore',
        'detail': 'Server -> Xerver'
    },
    {
        'offset': 0x135c78,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Input Mutex',
        'detail': 'Server -> Xerver'
    },
    {
        'offset': 0x135c90,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Input Semaphore',
        'detail': 'Server -> Xerver'
    },
    # Wait fix
    {
        'offset': 0x31afb,
        'original': bytes([0x6a, 0xff]),
        'patched': bytes([0x6a, 0x00]),
        'description': 'Fix UberClient mutex wait',
        'detail': 'INFINITE -> 0ms'
    },
]


def print_banner():
    print("=" * 70)
    print("  SimCity 2000 Network Edition v1.1 Patcher")
    print("  Enables TCP/IP mode for Windows 10/11 compatibility")
    print("=" * 70)
    print()


def calculate_md5(data):
    return hashlib.md5(data).hexdigest()


def verify_md5(file_path: str, expected_md5: str) -> Tuple[bool, str]:
    """
    Verify a file's MD5 checksum.

    Returns:
        Tuple of (matches: bool, actual_md5: str)
    """
    with open(file_path, 'rb') as f:
        actual_md5 = calculate_md5(f.read())
    return actual_md5 == expected_md5, actual_md5


def apply_patches(data, patches, filename):
    """Apply patches to binary data and return results."""
    data = bytearray(data)
    results = []

    for patch in patches:
        offset = patch['offset']
        original = patch['original']
        patched = patch['patched']

        if offset + len(original) > len(data):
            results.append({
                'status': 'OUT_OF_RANGE',
                'offset': offset,
                'description': patch['description'],
                'detail': patch.get('detail', '')
            })
            continue

        current = bytes(data[offset:offset + len(original)])

        if current == original:
            data[offset:offset + len(patched)] = patched
            results.append({
                'status': 'PATCHED',
                'offset': offset,
                'description': patch['description'],
                'detail': patch.get('detail', '')
            })
        elif current == patched:
            results.append({
                'status': 'ALREADY',
                'offset': offset,
                'description': patch['description'],
                'detail': patch.get('detail', '')
            })
        else:
            results.append({
                'status': 'MISMATCH',
                'offset': offset,
                'description': patch['description'],
                'detail': patch.get('detail', ''),
                'expected': original.hex(),
                'found': current.hex()
            })

    return bytes(data), results


def patch_file(input_path, output_path, patches, file_type, expected_size=None,
               expected_md5_patched=None, quiet=False):
    """
    Patch a single file.

    Args:
        input_path: Path to original file
        output_path: Path for patched output
        patches: List of patch definitions
        file_type: Label for output (e.g., "SERVER", "CLIENT")
        expected_size: Expected file size for validation
        expected_md5_patched: Expected MD5 of correctly patched file
        quiet: Suppress console output

    Returns:
        Tuple of (success: bool, md5: str or None)
    """
    filename = os.path.basename(input_path)

    if not quiet:
        print(f"[{file_type}] Processing: {filename}")
        print("-" * 50)

    # Read file
    if not os.path.exists(input_path):
        if not quiet:
            print(f"  ERROR: File not found: {input_path}")
        return False, None

    with open(input_path, 'rb') as f:
        data = f.read()

    # Check file size
    if not quiet:
        print(f"  Input:  {input_path}")
        print(f"  Size:   {len(data)} bytes")

    if expected_size and len(data) != expected_size:
        if not quiet:
            print(f"  WARNING: Expected {expected_size} bytes for v1.1")
            print(f"           This may be a different version")

    md5 = calculate_md5(data)
    if not quiet:
        print(f"  MD5:    {md5}")
        print()

    # Apply patches
    patched_data, results = apply_patches(data, patches, filename)

    # Print results
    patched_count = 0
    error_count = 0
    for r in results:
        status = r['status']
        if status == 'PATCHED':
            patched_count += 1
            if not quiet:
                print(f"  [OK] 0x{r['offset']:05X}: {r['description']}")
                if r['detail']:
                    print(f"       {r['detail']}")
        elif status == 'ALREADY':
            if not quiet:
                print(f"  [--] 0x{r['offset']:05X}: {r['description']} (already patched)")
        elif status == 'MISMATCH':
            error_count += 1
            if not quiet:
                print(f"  [!!] 0x{r['offset']:05X}: {r['description']} (MISMATCH)")
                print(f"       Expected: {r['expected']}")
                print(f"       Found:    {r['found']}")
        else:
            error_count += 1
            if not quiet:
                print(f"  [!!] 0x{r['offset']:05X}: {r['description']} ({status})")

    if not quiet:
        print()

    # Write output if any patches applied or already patched
    if error_count == 0 and (patched_count > 0 or any(r['status'] == 'ALREADY' for r in results)):
        with open(output_path, 'wb') as f:
            f.write(patched_data)
        if not quiet:
            print(f"  Output: {output_path}")
            print(f"  Applied {patched_count} new patch(es)")

        # Verify MD5 of patched file
        output_md5 = calculate_md5(patched_data)
        if expected_md5_patched:
            if output_md5 == expected_md5_patched:
                if not quiet:
                    print(f"  MD5:    {output_md5} (verified)")
            else:
                if not quiet:
                    print(f"  MD5:    {output_md5}")
                    print(f"  ERROR:  Expected {expected_md5_patched}")
                return False, output_md5
        else:
            if not quiet:
                print(f"  MD5:    {output_md5}")

        if not quiet:
            print()
        return True, output_md5
    else:
        if not quiet:
            print(f"  Errors encountered - check above")
        return False, None

    if not quiet:
        print()
    return True, None


def patch_v11(
    folder: str,
    output_suffix: str = '-v11',
    replace: bool = False,
    quiet: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """
    Patch SimCity 2000 Network Edition v1.1 binaries.

    Args:
        folder: Path to directory containing 2KSERVER.EXE and 2KCLIENT.EXE
        output_suffix: Suffix for output files (default: '-v11' -> '2KSERVER-v11.EXE')
                      Set to '' with replace=True to overwrite originals
        replace: If True and output_suffix='', overwrite original files
        quiet: Suppress output messages

    Returns:
        Tuple of (success: bool, details: dict)
        details contains 'server' and 'client' keys with patch results

    Example:
        from patch_sc2k_v11 import patch_v11

        success, details = patch_v11('/path/to/game')
        if success:
            print(f"Server: {details['server']['output']}")
            print(f"Client: {details['client']['output']}")
    """
    folder = os.path.abspath(folder)
    results = {'server': {}, 'client': {}}

    if not os.path.isdir(folder):
        return False, {'error': f'Folder not found: {folder}'}

    # Define paths
    server_in = os.path.join(folder, '2KSERVER.EXE')
    client_in = os.path.join(folder, '2KCLIENT.EXE')

    if output_suffix or replace:
        server_out = os.path.join(folder, f'2KSERVER{output_suffix}.EXE') if output_suffix else server_in
        client_out = os.path.join(folder, f'2KCLIENT{output_suffix}.EXE') if output_suffix else client_in
    else:
        return False, {'error': 'Must specify output_suffix or set replace=True'}

    if not quiet:
        print(f"Patching v1.1 binaries in: {folder}")

    # Patch server
    server_ok, server_md5 = patch_file(
        server_in, server_out, SERVER_V11_PATCHES, "SERVER",
        expected_size=553984,
        expected_md5_patched=EXPECTED_MD5['server_patched'],
        quiet=quiet
    )
    results['server'] = {
        'input': server_in,
        'output': server_out,
        'success': server_ok,
        'md5': server_md5,
        'expected_md5': EXPECTED_MD5['server_patched']
    }

    # Patch client
    client_ok, client_md5 = patch_file(
        client_in, client_out, CLIENT_V11_PATCHES, "CLIENT",
        expected_size=1422336,
        expected_md5_patched=EXPECTED_MD5['client_patched'],
        quiet=quiet
    )
    results['client'] = {
        'input': client_in,
        'output': client_out,
        'success': client_ok,
        'md5': client_md5,
        'expected_md5': EXPECTED_MD5['client_patched']
    }

    success = server_ok and client_ok

    if not quiet:
        if success:
            print(f"Successfully patched binaries in {folder}")
        else:
            print(f"Some patches failed - check details")

    return success, results


def main():
    print_banner()

    if len(sys.argv) < 2:
        print("Usage: python patch_sc2k_v11.py <path_to_v11_folder>")
        print()
        print("Example:")
        print('  python patch_sc2k_v11.py ./latest')
        print()
        print("The script will create:")
        print("  - 2KSERVER-v11.EXE (patched server)")
        print("  - 2KCLIENT-v11.EXE (patched client)")
        sys.exit(1)

    folder = sys.argv[1]

    if not os.path.isdir(folder):
        print(f"ERROR: Folder not found: {folder}")
        sys.exit(1)

    # Define paths
    server_in = os.path.join(folder, '2KSERVER.EXE')
    server_out = os.path.join(folder, '2KSERVER-v11.EXE')
    client_in = os.path.join(folder, '2KCLIENT.EXE')
    client_out = os.path.join(folder, '2KCLIENT-v11.EXE')

    print(f"Target folder: {folder}")
    print(f"Timestamp:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Patch server
    print("=" * 70)
    print("  SERVER PATCHES (13 total)")
    print("=" * 70)
    print()
    server_ok, server_md5 = patch_file(
        server_in, server_out, SERVER_V11_PATCHES, "SERVER",
        expected_size=553984,
        expected_md5_patched=EXPECTED_MD5['server_patched']
    )

    # Patch client
    print("=" * 70)
    print("  CLIENT PATCHES (8 total)")
    print("=" * 70)
    print()
    client_ok, client_md5 = patch_file(
        client_in, client_out, CLIENT_V11_PATCHES, "CLIENT",
        expected_size=1422336,
        expected_md5_patched=EXPECTED_MD5['client_patched']
    )

    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()

    if server_ok and client_ok:
        print("  All patches applied successfully!")
        print()
        print("  To play:")
        print(f"    1. Run: {server_out}")
        print(f"       - Select 'Internet' and click OK")
        print(f"       - Server listens on port 2586")
        print()
        print(f"    2. Run: {client_out}")
        print(f"       - Connect to server IP (use 127.0.0.1 for local)")
        print()
        print("  You can run multiple clients simultaneously.")
    else:
        print("  Some patches failed - check errors above")
        sys.exit(1)


if __name__ == '__main__':
    main()

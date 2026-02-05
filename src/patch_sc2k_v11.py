#!/usr/bin/env python3
"""
SimCity 2000 Network Edition v1.1 Patcher
==========================================
Patches 2KSERVER.EXE and 2KCLIENT.EXE (v1.1) to run on modern Windows (Windows 10/11)

Usage (CLI):
    python patch_sc2k_v11.py <path_to_folder_with_v11_files>

Usage (as module):
    from patch_sc2k_v11 import patch_v11
    success, details = patch_v11('/path/to/binaries')
"""

import sys
import os
import hashlib
from datetime import datetime
from typing import Tuple, Dict, Any

# =============================================================================
# EXPECTED MD5 CHECKSUMS
# =============================================================================
EXPECTED_MD5 = {
    'server_original': '6c412cf27726879aaa97d75db857a601',
    'client_original': '9942b057f14fa995cfe8d710e6c1b9bf',
    'server_patched': 'b1c0e0dd00aeb46f8909caccb1a81682',
    'client_patched': '8054b63d77a09fcebaf944f8e6d9f451',
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
    # IPC name scrambling (Server -> Xerver) - must match client
    {
        'offset': 0x761c8,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Output Mutex',
        'detail': 'Server -> Xerver'
    },
    {
        'offset': 0x761dc,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Output Semaphore',
        'detail': 'Server -> Xerver'
    },
    {
        'offset': 0x761f4,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Input Mutex',
        'detail': 'Server -> Xerver'
    },
    {
        'offset': 0x76208,
        'original': bytes([0x53]),
        'patched': bytes([0x58]),
        'description': 'Scramble IPC: Server Input Semaphore',
        'detail': 'Server -> Xerver'
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
]

# =============================================================================
# V1.1 CLIENT PATCHES (2KCLIENT.EXE - 1,422,336 bytes)
# =============================================================================
CLIENT_V11_PATCHES = [
    # Singleton bypass - 4 checks total
    {
        'offset': 0x3487c,
        'original': bytes([0x74, 0x39]),
        'patched': bytes([0xEB, 0x39]),
        'description': 'Skip Server Process Mutex check 1',
        'detail': 'JE -> JMP'
    },
    {
        'offset': 0x387c0,
        'original': bytes([0x74, 0x41]),
        'patched': bytes([0xEB, 0x41]),
        'description': 'Skip Server Process Mutex check 2',
        'detail': 'JE -> JMP'
    },
    {
        'offset': 0x64554,
        'original': bytes([0x0F, 0x85, 0x90, 0x00, 0x00, 0x00]),
        'patched': bytes([0xE9, 0x91, 0x00, 0x00, 0x00, 0x90]),
        'description': 'Skip Server Process Mutex check 3',
        'detail': 'JNE near -> JMP near'
    },
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


def calculate_md5(data):
    return hashlib.md5(data).hexdigest()


def apply_patches(data, patches):
    data = bytearray(data)
    results = []
    for patch in patches:
        offset = patch['offset']
        original = patch['original']
        patched = patch['patched']
        current = bytes(data[offset:offset + len(original)])
        if current == original:
            data[offset:offset + len(patched)] = patched
            results.append({'status': 'PATCHED', 'offset': offset,
                          'description': patch['description'], 'detail': patch.get('detail', '')})
        elif current == patched:
            results.append({'status': 'ALREADY', 'offset': offset,
                          'description': patch['description'], 'detail': patch.get('detail', '')})
        else:
            results.append({'status': 'MISMATCH', 'offset': offset,
                          'description': patch['description'], 'detail': patch.get('detail', ''),
                          'expected': original.hex(), 'found': current.hex()})
    return bytes(data), results


def patch_file(input_path, output_path, patches, file_type, expected_size=None, quiet=False):
    if not os.path.exists(input_path):
        if not quiet:
            print(f"  ERROR: File not found: {input_path}")
        return False, None

    with open(input_path, 'rb') as f:
        data = f.read()

    if not quiet:
        print(f"[{file_type}] Processing: {os.path.basename(input_path)}")
        print(f"  Size: {len(data)} bytes, MD5: {calculate_md5(data)}")

    patched_data, results = apply_patches(data, patches)

    patched_count = sum(1 for r in results if r['status'] == 'PATCHED')
    error_count = sum(1 for r in results if r['status'] == 'MISMATCH')

    if not quiet:
        for r in results:
            if r['status'] == 'PATCHED':
                print(f"  [OK] 0x{r['offset']:05X}: {r['description']}")
            elif r['status'] == 'ALREADY':
                print(f"  [--] 0x{r['offset']:05X}: {r['description']} (already)")
            else:
                print(f"  [!!] 0x{r['offset']:05X}: {r['description']} MISMATCH")

    if error_count == 0:
        with open(output_path, 'wb') as f:
            f.write(patched_data)
        md5 = calculate_md5(patched_data)
        if not quiet:
            print(f"  Output: {output_path}")
            print(f"  MD5: {md5}")
        return True, md5
    return False, None


def patch_v11(folder: str, output_suffix: str = '-v11', quiet: bool = False) -> Tuple[bool, Dict[str, Any]]:
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        return False, {'error': f'Folder not found: {folder}'}

    server_in = os.path.join(folder, '2KSERVER.EXE')
    server_out = os.path.join(folder, f'2KSERVER{output_suffix}.EXE')
    client_in = os.path.join(folder, '2KCLIENT.EXE')
    client_out = os.path.join(folder, f'2KCLIENT{output_suffix}.EXE')

    if not quiet:
        print(f"Patching v1.1 binaries in: {folder}\n")

    server_ok, server_md5 = patch_file(server_in, server_out, SERVER_V11_PATCHES, "SERVER", quiet=quiet)
    if not quiet:
        print()
    client_ok, client_md5 = patch_file(client_in, client_out, CLIENT_V11_PATCHES, "CLIENT", quiet=quiet)

    return server_ok and client_ok, {
        'server': {'output': server_out, 'success': server_ok, 'md5': server_md5},
        'client': {'output': client_out, 'success': client_ok, 'md5': client_md5}
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python patch_sc2k_v11.py <folder>")
        sys.exit(1)
    success, details = patch_v11(sys.argv[1])
    sys.exit(0 if success else 1)

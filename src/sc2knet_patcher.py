"""
SimCity 2000 Network Edition - Interoperability Patch v1.5
Pure Python implementation of all binary patches.

Patch data is loaded from individual JSON files in:
    src/patches/interoperability/

Usage:
    python sc2knet_patcher.py <game_directory>

    Where <game_directory> contains the unpatched v1.1 update files:
        2KCLIENT.EXE, 2KSERVER.EXE, USARES.DLL, USAHORES.DLL,
        MAXHELP.EXE, WINSCURK.EXE
"""

import hashlib
import json
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
# PATCH LOADER
# =============================================================================

def load_patches() -> dict:
    """
    Load all interoperability patches from JSON files in
    src/patches/interoperability/, ordered by filename.

    Returns a dict mapping target filename -> patch data dict, preserving
    the order of the numbered patch files.
    """
    patches_dir = Path(__file__).parent / "patches" / "interoperability"
    patches = {}

    for patch_file in sorted(patches_dir.glob("*.json")):
        with open(patch_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        target = data["target"]
        patches[target] = {
            "new_size": data["new_size"],
            "triples": [tuple(t) for t in data["triples"]],
            "diff_mods": {int(k): v for k, v in data["diff_mods"].items()},
            "extra": bytes.fromhex(data["extra"]) if data["extra"] else b"",
            "pre_md5": data["pre_md5"],
            "post_md5": data["post_md5"],
        }

    return patches


# =============================================================================
# PATCHING FUNCTIONS
# =============================================================================

def patch_file(filepath: str, patch_data: dict, backup: bool = True) -> bool:
    """
    Apply a patch to a single file.

    Args:
        filepath:   Path to the file to patch.
        patch_data: Patch definition dict from load_patches().
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

    patches = load_patches()
    all_ok = True
    for filename, patch_data in patches.items():
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

    patches = load_patches()
    print("Verifying patched files...")
    for filename, patch_data in patches.items():
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
        patches = load_patches()
        if filename not in patches:
            print(f"Unknown file: {filename}")
            print(f"Available: {', '.join(patches.keys())}")
            sys.exit(1)
        ok = patch_file(os.path.join(game_dir, filename), patches[filename])
        sys.exit(0 if ok else 1)

    ok = patch_all(game_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

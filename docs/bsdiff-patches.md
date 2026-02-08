# SimCity 2000 Network Edition - Binary Patch Documentation

This document describes the bsdiff binary patches applied by the Interoperability Patch
Setup Script (IPSS) v1.5 to SimCity 2000 Network Edition files.

## Overview

The IPSS applies binary patches to six game files using **bspatch** (part of the
[bsdiff/bspatch](http://www.daemonology.net/bsdiff/) toolset v4.3, Win32 port by
Andreas John). The patches transform the official v1.1 update files (or the retail
originals, for files not included in the update) into interoperability-patched versions
that work on modern Windows systems with network play support.

The retail ISO is available from:
https://archive.org/details/simcity2000networkedition

The patch tool binary is located at:
```
_setup/_tools/bsdiff/bspatc'h.exe
```
(The apostrophe in the filename is intentional.)

## Patch File Format

All patch files use the **BSDIFF40** format:
- **Magic**: `BSDIFF40` (8 bytes)
- **Control block size**: int64 (8 bytes) — bzip2-compressed length of control data
- **Diff block size**: int64 (8 bytes) — bzip2-compressed length of diff data
- **New file size**: int64 (8 bytes) — size of the output file
- **Control block**: bzip2-compressed stream of (add, insert, seek) triples
- **Diff block**: bzip2-compressed bytewise differences
- **Extra block**: bzip2-compressed stream of new bytes for insertions

Patch files are located in: `_setup/_tools/bsdiff/patch/`

## Patch Inventory

### 1. WINSCURK.EXE.patch
| Field | Value |
|---|---|
| **Patch size** | 206 bytes |
| **Source MD5** | `4E74E05ACA5B7F73E2E91B4222E397DF` |
| **Target MD5** | `C5AC16701CFE62DE87103BF4F4E74248` |
| **Output size** | 2,092,216 bytes (0x1FECB8) |
| **Source origin** | Retail install — not overwritten by v1.1 update |
| **Setup label** | `:p_0` |
| **Notes** | The `.old` file is preserved (not deleted) after patching |

### 2. 2KCLIENT.EXE.patch
| Field | Value |
|---|---|
| **Patch size** | 1,619 bytes |
| **Source MD5** | `9942B057F14FA995CFE8D710E6C1B9BF` |
| **Target MD5** | `6DEB7E19030CDE50FBD5BA0AAE699FE4` |
| **Output size** | 1,422,336 bytes (0x15B400) |
| **Source origin** | v1.1 update (`Update2KNet11.exe`) |
| **Setup label** | `:p_1` |

### 3. 2KSERVER.EXE.patch
| Field | Value |
|---|---|
| **Patch size** | 783 bytes |
| **Source MD5** | `6C412CF27726879AAA97D75DB857A601` |
| **Target MD5** | `F5E61FC87EA2023B55D7456E694F5D25` |
| **Output size** | 553,984 bytes (0x87400) |
| **Source origin** | v1.1 update (`Update2KNet11.exe`) |
| **Setup label** | `:p_2` |

### 4. USARES.DLL.patch
| Field | Value |
|---|---|
| **Patch size** | 506 bytes |
| **Source MD5** | `05B105B841E3FE34FE7F37CAE67B6D74` |
| **Target MD5** | `F4139EC4ECAEEF79E219AFB9F41BB90D` |
| **Output size** | 1,471,488 bytes (0x167400) |
| **Source origin** | v1.1 update (`Update2KNet11.exe`) only |
| **Setup label** | `:p_3` |

### 5. USAHORES.DLL.patch
| Field | Value |
|---|---|
| **Patch size** | 202 bytes |
| **Source MD5** | `A3CF6380BF74DF2E8E266122F3BFA276` |
| **Target MD5** | `865FCD4BDA8341B978C3701BE9E0A6F7` |
| **Output size** | 29,696 bytes (0x7400) |
| **Source origin** | v1.1 update (`Update2KNet11.exe`) only |
| **Setup label** | `:p_4` |

### 6. MAXHELP.EXE.patch
| Field | Value |
|---|---|
| **Patch size** | 152 bytes |
| **Source MD5** | `4966A5EA9D79518241DD587F0E0BD135` |
| **Target MD5** | `5119465EFFC9DEAA02CA1899A0F8F4AA` |
| **Output size** | 33,280 bytes (0x8200) |
| **Source origin** | Retail install — not included in v1.1 update |
| **Setup label** | `:p_5` |

## Patching Workflow

The setup script (`_setup.cmd`) follows this sequence for each file:

1. **Validate** the current file against the expected post-patch MD5 (target hash)
2. If validation fails, **check** the pre-patch MD5 (source hash); if that also fails,
   re-copy the file from the appropriate source (update or retail install)
3. **Rename** the original to `<FILENAME>.old`
4. **Apply** the bsdiff patch: `bspatc'h.exe <old> <new> <patchfile>`
5. **Delete** the `.old` file (except for `WINSCURK.EXE`, which is kept)

### Source File Provenance

Files come from two source installers, each extracted via FineSplit + STIX:

| Source | Installer | MD5 | Files Provided |
|---|---|---|---|
| Retail | Install CD ISO ([archive.org](https://archive.org/details/simcity2000networkedition)) | — | 2KCLIENT, 2KSERVER, MAXHELP, WINSCURK, game data, WEBSTER.OCX |
| v1.1 Update | `Update2KNet11.exe` | `2C3CCAC00E8410D73CBEA858B9D25159` | 2KCLIENT, 2KSERVER, USARES.DLL, USAHORES.DLL |

The v1.1 update overwrites the retail versions of 2KCLIENT.EXE and 2KSERVER.EXE.
The patches are then applied on top of the v1.1 versions (for files included in the
update) or the retail versions (for MAXHELP.EXE and WINSCURK.EXE).

## Additional Interoperability Files

Beyond the binary patches, the IPSS also deploys these non-patched files:

| File | Purpose |
|---|---|
| `portable.dll` | PE32 DLL — enables portable/non-registry operation |
| `dplay.dll` | PE32 DLL — DirectPlay compatibility shim |
| `2kclient.exe.manifest` | Side-by-side assembly manifest declaring dependency on `webster.xco` v2.0 |
| `maxhelp.exe.manifest` | Same manifest as above for MAXHELP.EXE |
| `webster.xco.manifest` | Registration-free COM manifest for `WEBSTER.OCX` (CLSID `{FF0A47B0-5CAC-11CE-ACAF-00AA004CA344}`) |

These manifests enable registration-free COM activation so `WEBSTER.OCX` works without
running `regsvr32`, allowing the game to run portably.

## Network Configuration

The game uses **TCP port 2586**. The IPSS includes helper scripts and a UPnP client
(`upnpc-static.exe`) for automatic port forwarding:

| Script | Function |
|---|---|
| `host.cmd` | Starts 2KSERVER.EXE, enables UPnP port forward, shows public IP |
| `play.cmd` | Starts 2KCLIENT.EXE |
| `port 2586 - enable.bat` | UPnP: add TCP 2586 forwarding rule |
| `port 2586 - check.bat` | UPnP: verify forwarding rule exists |
| `port 2586 - disable.bat` | UPnP: remove TCP 2586 forwarding rule |
| `what is my ip.bat` | UPnP: query external IP, falls back to icanhazip.com |

## Notes for Python Reimplementation

When building a Python equivalent of the bspatch functionality:

- The BSDIFF40 format stores three bzip2-compressed streams concatenated after the
  32-byte header. Python's `bz2` module can decompress these.
- **Important**: Header and control integers use **sign-magnitude** encoding, NOT
  two's complement. Bit 7 of the high byte is the sign flag; the remaining 63 bits
  are the unsigned magnitude. Do NOT use `struct.unpack('<q', ...)` — it will
  silently produce wrong values. See `_offtin()` in `code/apply_patches.py`.
- The control block contains triples of (add_len, insert_len, seek_offset), each as
  sign-magnitude int64 LE.
- The "add" operation reads `add_len` bytes from both the diff stream and the old file,
  summing them bytewise (mod 256) into the output.
- The "insert" operation copies `insert_len` bytes verbatim from the extra stream.
- The "seek" operation adjusts the read position in the old file by `seek_offset`.
- MD5 checksums from the setup script should be used for pre/post validation.
- Reference implementations exist: see the original C source at
  http://www.daemonology.net/bsdiff/ and various Python ports on PyPI (`bsdiff4`).

# Patch Explanation

## What This Is

SimCity 2000 Network Edition shipped in 1996 and received one official update (v1.1).
Neither version works correctly on modern Windows due to missing DirectPlay support,
COM registration requirements, and other compatibility issues.

The interoperability patches are small binary diffs that fix these problems, allowing
the game to run portably on modern systems with working network multiplayer.

## What Gets Patched

Six files are patched. Each patch targets a specific binary from the retail install
(or v1.1 update) identified by its MD5 checksum, producing a fixed binary with a
known output checksum. The retail ISO is available from
[archive.org](https://archive.org/details/simcity2000networkedition).

| File | Type | Changes | What the patch does |
|---|---|---|---|
| `2KCLIENT.EXE` | Game client | 113 regions | DirectPlay shims, registry-free config, sleep injection, crash fixes, render pipeline fix, `ADVAPI32`->`portable` import redirect, window class renames |
| `2KSERVER.EXE` | Game server | 55 regions | COM vtable redirects, sleep injection, default IP to 127.0.0.1, `ADVAPI32`->`portable`, window class renames, "Your Name"->"Nobody" |
| `USARES.DLL` | Resource library (USA locale) | 106 regions | Dialog layout repositioning, menu text rewording, ~70 palette color fixes (`0x10`->`0x00`), newline-to-space fixes in strings |
| `USAHORES.DLL` | Resource library (USA hostile) | 28 regions | "AXIS"->"axis" case fix, dialog resize, "Join Existing Game" text blanked |
| `WINSCURK.EXE` | Scenario editor | 4 regions | Resource DLL name fix (`%s.DL`->`USA.DLL`), two `ADVAPI32`->`portable` import redirects |
| `MAXHELP.EXE` | Help viewer | 1 region | Dialog style flag fix (`0x54`->`0x11`) for modern Windows display |

The first four come from the v1.1 update; WINSCURK.EXE and MAXHELP.EXE come from
the retail install (they were not updated in v1.1).

## How Patching Works

Patches use the **BSDIFF40** binary diff format. A patch file encodes only the byte-level
differences between the old and new file, compressed with bzip2. This keeps patch files
tiny (152 bytes to 1.6 KB) even for multi-megabyte executables.

The patching process:
1. Verify the source file MD5 matches the expected unpatched checksum
2. Apply the binary diff to produce the new file in memory
3. Verify the output MD5 matches the expected patched checksum
4. Write the output only after both checksums pass

If any checksum fails, nothing is written.

## Supporting Files

The patches alone aren't enough — the game also needs these companion files dropped
alongside the binaries:

| File | Why |
|---|---|
| `portable.dll` | Redirects registry/path lookups so the game runs from any folder |
| `dplay.dll` | DirectPlay shim — the original DirectPlay API was removed from modern Windows |
| `*.manifest` files | Enable registration-free COM so `WEBSTER.OCX` works without `regsvr32` |

## Running the Patcher

Python based patching has been implemented. Refer to the original README.md file to run the patches.
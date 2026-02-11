# Patch Detail Log

Human-readable record of every byte-level modification applied to SimCity 2000
Network Edition binaries. This document grows as new patch sets are added.

---

## Patch Set 1: Interoperability (v1.1-fixed)

**Purpose**: Fix compatibility with modern Windows and enable portable network play.
**Source**: IPSS v1.5 bsdiff patches (`interop/_setup/_tools/bsdiff/patch/`)
**Total changed bytes**: 2,137 across 6 files (155 change regions)

---

### 2KCLIENT.EXE

**67 change regions, 1,116 changed bytes** | 1,422,336 bytes (unchanged size)
Source MD5: `9942b057f14fa995cfe8d710e6c1b9bf`
Target MD5: `6deb7e19030cde50fbd5ba0aae699fe4`

#### PE Header

Zero out checksum and security directory fields:

```
0x000121  old: 50 15    new: 00 00    ; PE checksum (high word)
0x000124  old: 58 F2    new: 00 00    ; PE checksum (low word)
```

#### DLL Import Redirect

Redirect ADVAPI32.DLL import to portable.dll for registry-free operation:

```
0x147AB4  old: "ADVAPI32"
          new: "portable"
```

#### DirectPlay / COM Initialization Code

Patch out original DirectPlay COM initialization and replace with shims:

```
0x008D03  old: 6A 00          new: EB 22          ; JMP over original CoCreateInstance call
0x008D22  old: E8 21 CD 0E 00 new: 50 6A 00 EB 43 ; replace CALL with PUSH EAX, PUSH 0, JMP
0x008D68  old: 6A 00          new: EB B8          ; JMP backward to new handler
```

New DirectPlay session handler injected at 0x008D94 (44 bytes):
```
0x008D94  89 86 9C 00 00 00 58 83 F8 01 75 20 8B 46 1C 85  ; MOV [ESI+9C],EAX; POP EAX; CMP EAX,1
0x008DA4  C0 74 19 6A 01 50 FF 15 F8 05 55 00 85 C0 74 0C  ; JZ skip; PUSH 1; PUSH EAX; CALL [550005F8]
0x008DB4  6A 00 6A 00 68 F5 00 00 00 50 FF D7              ; PUSH 0; PUSH 0; PUSH F5; PUSH EAX; CALL EDI
```

#### Window Class Registration

Replace `push` of window class string + `call` with direct `call` to new registrars
(written into INT3 padding at 0x00A010–0x00A06B):

```
0x008FD5  old: 68 F4 7D 53 00  new: E8 36 10 00 00  ; PUSH addr -> CALL 0x00A010
0x009027  old: C7 46 3E 01 ..  new: E8 04 10 00 .. 90 90  ; MOV [ESI+3E],1 -> CALL 0x00A030; NOP
0x009075  old: C7 46 56 ..     new: E8 D6 0F .. 90 90     ; MOV [ESI+56],.. -> CALL 0x00A050; NOP
```

New registrar functions at 0x00A010, 0x00A030, 0x00A050 each call
`RegQueryValueExA` with different registry key names (`0x53BFE8`, `0x53BFF0`,
`0x53BFF8`) and store the result.

#### Registry-free Configuration Loading

New configuration loader at 0x036007 (replaces INT3 padding):
```
0x036007  old: E8 A1 C9 FC FF C3 CC...  ; original CALL + RET + padding
          new: 50 E8 A0 C9 FC FF        ; PUSH EAX; CALL original
               8B 0D E4 91 54 00        ; MOV ECX,[5491E4]
               68 30 C0 53 00           ; PUSH "..."
               EB 59                    ; JMP to continuation
```

Companion functions at 0x0360B5 and 0x0360D2 handle secondary key lookups
via `RegQueryValueExA` and store into global `[53C128]`.

#### Window Activation / Sleep Guard

Force sleep after `CoInitialize`:
```
0x036A59  old: 5D 5F 5E 5B C3 CC...   ; POP EBP; POP EDI; POP ESI; POP EBX; RET + padding
          new: 6A 01 FF 15 04 03 55 00 ; PUSH 1; CALL [Sleep]; then original epilog
               5D 5F 5E 5B C3
```

#### DirectPlay Session Cleanup / Multiplayer Fixes

Skip registry-based DirectPlay service provider enumeration:
```
0x031AD2  old: 68 9C A7 53 00  new: 90 90 90 90 90  ; NOP out PUSH of SP GUID string
0x031ADA  old: 57              new: 90              ; NOP out PUSH EDI
0x031ADE  old: 8D 45 E4        new: 90 90 90        ; NOP out LEA EAX,[EBP-1C]
0x031AE7  old: 50              new: 90              ; NOP out PUSH EAX
0x031AF5  old: FF 15 14 03 55 00 6A FF A3 6C 71 54 00 50 FF 15 0C 03 55 00
          new: 90*8  89 3D 6C 71 54 00 90*4  ; NOP; MOV [54716C],EDI; NOP
```

New multiplayer session handler at 0x03383F (replaces INT3 padding):
```
0x0337CF  old: FF D3          new: EB 6E          ; JMP to new handler at 0x03383F
0x03383F  FF D3                                    ; CALL EBX (original)
          A1 A0 E8 53 00                           ; MOV EAX,[53E8A0]
          85 C0 74 87                              ; TEST EAX,EAX; JZ back
          8B 4D F0                                 ; MOV ECX,[EBP-10]
          68 18 E8 53 00 50 6A 10 51 FF D3         ; PUSH; CALL EBX with new args
          E9 74 FF FF FF                           ; JMP back to main flow
```

#### Chat Window / IPC Fixes

Redirect jump to new code cave at 0x0380B0 (old bytes are CC INT3 padding):
```
0x038092  old: 91 A2 FC FF  new: 1A 00 00 00   ; change relative jump target to 0x0380B0
0x0380B0  [INSERT into INT3 code cave]
          83 3D 28 C1 53 00 00 75 01 C3        ; CMP [53C128],0; JNZ +1; RET (skip if unconfigured)
```

#### Buffer Overrun Guard

```
0x052EF7  old: 68 00 01 00 00  new: EB 2C 90 90 90  ; JMP over original PUSH 256
0x052F25  83 F9 00 7E F3 68 00 01 00 00 EB CB       ; CMP ECX,0; JLE retry; PUSH 256; JMP back
```

#### Network I/O Restructuring

Rewrite virtual call dispatch for portable DirectPlay:
```
0x063E71  old: 8B 88  new: EB 43  ; JMP over original vtable call
0x0645F1  old: 68 A8 C0 53 00 8D 45 CC 6A 01 50 FF
          new: 33 C0 A3 EC 91 54 00 E9 A6 00 00 00  ; XOR EAX,EAX; store; JMP
```

#### Sleep Injection for CPU Throttling

New sleep code at 0x076DAF:
```
0x076DAF  old: 53 FF 15 04 03 55 00  ; PUSH EBX; CALL [Sleep]
          new: EB 27 90*5             ; JMP to 0x076DD8
0x076DD8  6A 01 FF 15 04 03 55 00 EB D4  ; PUSH 1; CALL [Sleep]; JMP back
```

#### Safe Window Title Fallback

Null-check on window class name before use:
```
0x07A7C8  8B 54 24 0C 85 D2 75 08 C7 44 24 0C 30 77 53 00  ; if param3==NULL, use "0wS"
0x07A7D8  8B 54 24 14 85 D2 75 08 C7 44 24 14 30 77 53 00  ; if param5==NULL, use "0wS"
0x07A7E8  53 56 EB 26                                        ; JMP to original PUSH EBX,ESI
0x07A810  old: 53 56  new: EB B6                             ; JMP back to null checks
```

#### Crash Fix: Scenario Load

```
0x08CD17  old: E9 A0 02 00 00  new: 90 90 90 90 90  ; NOP out problematic JMP
0x08CD6A  old: E9 4D 02 00 00  new: 90 90 90 90 90  ; NOP out second JMP
0x08DC50  old: 02              new: 03              ; fix off-by-one in scenario index
```

#### Render Pipeline Fix

New bounds check at 0x0E3F70 (replaces INT3 padding):
```
0x0E501A  old: 74 0D 55 57 BD 01 00 00 00
          new: E9 51 EF FF FF 90*4         ; JMP 0x0E3F70; NOP padding
0x0E3F70  0F 84 B3 10 00 00              ; JZ original_continue
          81 7C 24 5C 2C 01 00 00        ; CMP [ESP+5C], 0x12C
          0F 84 A5 10 00 00              ; JZ original_continue
          55 57 BD 01 00 00 00           ; PUSH EBP; PUSH EDI; MOV EBP,1
          E9 93 10 00 00                 ; JMP back
```

#### Portable DPlay Config Read

New configuration reader at 0x0FBFDF (60 bytes, replaces INT3 padding):
```
0x0FBFDF  51                             ; PUSH ECX
          6A 03 57 FF 15 E4 05 55 00    ; CreateFileA(path, GENERIC_READ|WRITE)
          85 C0 74 28                    ; TEST EAX,EAX; JZ skip
          A3 A0 E8 53 00                ; MOV [53E8A0],EAX (store handle)
          68 00 04 00 00 6A 10           ; PUSH 1024; PUSH 16
          68 18 E8 53 00                 ; PUSH buffer addr
          6A 03 57 FF 15 6C 05 55 00    ; ReadFile
          68 00 04 00 00 6A 03 57       ; PUSH 1024; PUSH 3; PUSH EDI
          FF 15 70 05 55 00              ; GetFileSize
          59 E9 83 82 FE FF              ; POP ECX; JMP back
```

#### Import Table Patch

```
0x118758–0x118784  Various import descriptor table entries modified
                   to add new function imports for portable.dll
```

#### String / Branding Renames

Window class identifiers renamed from original Maxis names to unique names,
preventing conflicts with other running instances:

```
0x135C38  "HereIAm\0\0\0\0\0Server" -> "2KNetC_\0\0\0\0\02KNetC"  ; mutex (18 bytes, null-separated)
0x135C5C  "Server"       -> "2KNetC"            ; window class name
0x135C78  "Server"       -> "2KNetC"            ; window class name
0x135C90  "Server"       -> "2KNetC"            ; window class name
0x13928C  "Server"       -> "2KNetC"            ; session name
0x13AAA8  "Client"       -> "2KNetC"            ; client->2KNetC rename
0x1367F4  "UberClient C" -> "2KNetC Uber "      ; display name (starts with 'U' not '\0')
0x13919C  "UberClient Process Mutex" -> "2KNetC Uber Process Mutex" ; (24 bytes)
0x13A9E8  "\0\0\0\0"     -> "News"              ; new menu label
0x13A9F0  "\0\0\0\0"     -> "Goto"              ; new menu label
0x13A9F8  "\0\0\0\0\0\0" -> "Budget"            ; new menu label
0x13B394  "IT BLEEDS IT LEADS SEMAPHORE" -> "2KNetC Newspaper Semaphore\0_"  ; (28 bytes)
0x13C77C  "SIMCITY_ONLINE_NEWSPAPER_MUTEX" -> "2KNetC Newspaper Mutex\0_______" ; (30 bytes)
0x13C78D  "W"            -> "M"                 ; from "NEWSPAPER" -> "Mutex" context
0x13926B  "2"            -> "_"                 ; separator
0x13D764  "2"            -> "_"                 ; separator
```

---

### 2KSERVER.EXE

**35 change regions, 737 changed bytes** | 553,984 bytes (unchanged size)
Source MD5: `6c412cf27726879aaa97d75db857a601`
Target MD5: `f5e61fc87ea2023b55d7456e694f5d25`

#### PE Header

```
0x000121  old: D0 08  new: 00 00  ; PE checksum zeroed
0x000124  old: 68 6A  new: 00 00
```

#### DLL Import Redirect

```
0x07D624  old: "ADVAPI32"  new: "portable"  ; registry-free operation
```

#### COM Virtual Call Redirection

Replace vtable dispatches with direct calls for portable DirectPlay:
```
0x0019F3  old: FF 50 2C 8B 08           new: E9 D8 7C 06 00  ; JMP to new handler at 0x0696D0
0x001A22  old: FF 90 80 00 00 00        new: E8 C9 7C 06 00 90 ; CALL new handler; NOP
0x0157B5  old: FF 90 80 00 00 00        new: E8 36 3F 05 00 90 ; CALL new handler; NOP
```

New COM dispatch handlers at 0x0696C2 (78 bytes):
```
0x0696C2  CC CC CC CC CC CC            ; alignment padding
          48 A2 46 00                  ; address constant
          50 69 41 00                  ; address constant
          8B 41 08 8B 00 8B 00        ; MOV EAX,[ECX+8]; deref vtable
          A3 D4 56 47 00              ; MOV [4756D4],EAX
          BE D4 56 47 00              ; MOV ESI,4756D4
          BF C8 A2 46 00              ; MOV EDI,46A2C8
          ...
          8B 41 0A 85 C0 74 12        ; check path string
          80 38 00 74 0D              ; null check
          80 38 5C 74 08              ; backslash check
          40 80 38 00 74 09 EB F3    ; advance pointer
          C7 41 0A CC 56 47 00       ; set default path
```

#### Window Class Registration Fix

```
0x003CFD  old: C1  new: 1A  ; fix jump offset in class registration
0x003D16  old: B8 01 00 00 00 5F 5E 5B 83 C4 08 C2 08 00 B8 01 00
          new: EB 0D                          ; JMP to sleep injection
               6A 01 FF 15 E0 98 48 00       ; PUSH 1; CALL [Sleep]
               EB 9D                          ; JMP back to retry
               90 90 5D B8 01 .. 00           ; NOP; POP EBP; MOV EAX,1; adjusted epilog
```

#### NOP Out Registry-based Service Provider

```
0x03EEA7  old: 68 34 A3 47 00  new: 90 90 90 90 90  ; NOP out PUSH of SP GUID
0x03EEB1  old: 56              new: 90              ; NOP out PUSH ESI
0x03EEC2  old: 57 FF 15 1C 99 48 00
          new: 33 C0 90 90 90 90 90  ; XOR EAX,EAX; NOP (skip registry call)
```

#### Miscellaneous Code Fixes

```
0x00AB74  old: 68 7C 5A 47 00  new: 6A 00 90 90 90  ; PUSH 0 instead of window title string
0x0108A8  old: 02              new: 04              ; timer interval adjustment
0x010B5D  old: 68 55 02 00 00 E8 07 34 05 00
          new: 58 58 90*8                           ; POP; POP; NOP (skip error message box)
0x01D633  old: 6A 00           new: EB 1F           ; skip ahead past redundant init
0x025EB2  old: 90 D0 03        new: 10 27 00        ; change constant 250000 -> 10000
0x025EC7  old: 90 D0 03        new: 10 27 00        ; same constant in second location
0x025ED4  old: CC CC CC CC     new: 24 24 24 5E     ; "$$&^" - format string patch
```

#### Sleep Injection

```
0x04878D  old: 5E 81 C4 CC 00 00 00 C3 CC*5
          new: 96                              ; XCHG ESI,EAX
               6A 01 FF 15 E0 98 48 00       ; PUSH 1; CALL [Sleep]
               96                              ; XCHG ESI,EAX
               5E 81 C4 00 00 00 C3           ; original epilog
```

#### Default IP Address

Hardcoded IP changed from original Maxis server to localhost:
```
0x0734BC  "00.9.253" -> "27.0.0.1"    ; (part of "100.9.253" -> "127.0.0.1")
          (plus two more occurrences via INSERTs at 0x073504 and 0x073548)
```

#### String / Branding Renames

```
0x0761C0  "HereIAm\0"    -> "2KNetS_\0"         ; mutex prefix (8 bytes, null at +7)
0x0761C8  "Server"       -> "2KNetS"            ; within mutex block
0x0761DC  "Server"       -> "2KNetS"            ; window class name
0x0761F4  "Server"       -> "2KNetS"            ; window class name
0x076208  "Server"       -> "2KNetS"            ; window class name
0x073A68  "Server"       -> "2KNetS"            ; session name
0x0787F8  "Server"       -> "2KNetS"            ; version info
0x07871C  "Client"       -> "2KNetS"            ; client->server rename
0x073ACC  "Your Name"    -> "Nobody\0\0\0"      ; default player name
0x0738EC  "UberClient Process Mutex" -> "2KNetS Uber Process Mute" ; (24 bytes)
0x078734  "UberClient C" -> "2KNetS Uber "      ; display name (starts with 'U' not '\0')
0x073A58  "2"            -> "_"                 ; separator
0x073E7C  "IT BLEEDS IT LEADS SEMAPHORE" -> "2KNetS Newspaper Semaphore\0_" ; (28 bytes)
0x07892C  "SIMCITY_ONLINE_NEWSPAPER_MUTEX" -> "2KNetS Newspaper Mutex\0_______" ; (30 bytes)
```

#### Maxis Branding Case Change (UTF-16LE)

```
0x07DE0E  "A" -> "a"  ; "MAXIS" -> "Maxis" (UTF-16LE: bytes at 0E,10,12,14)
0x07DE10  "X" -> "x"
0x07DE12  "I" -> "i"
0x07DE14  "S" -> "s"
```

---

### USARES.DLL

**45 change regions, 229 changed bytes** | 1,471,488 bytes (unchanged size)
Source MD5: `05b105b841e3fe34fe7f37cae67b6d74`
Target MD5: `f4139ec4ecaeef79e219afb9f41bb90d`

#### Dialog Layout Adjustments

Reposition/resize dialog controls (coordinates stored as 16-bit LE in
resource section):

```
0x0098B0  old: 69  new: 29  ; control position adjustment
0x0098DB  old: 50  new: 48  ; button width: 80 -> 72
0x0098E2  old: 04 00  new: EE FF  ; y-offset: +4 -> -18
0x009913  old: 50  new: 48  ; button width
0x00991A  old: 19 00  new: EE FF  ; y-offset: +25 -> -18
0x009947  old: 50  new: 48  ; button width
0x00994E  old: 2C 00  new: EE FF  ; y-offset: +44 -> -18
0x00997A  old: 41  new: 04  ; control style flag
0x0099A6  old: 54  new: 17  ; control style flag
```

#### Menu / Label Text Changes

Budget dialog labels (UTF-16LE encoded):
```
0x00A46E  old: 00 00 00 00  new: 03 08 19 80  ; dialog resource header flags
0x00A49A  "Auto Budget" -> "Budget\0\0\0\0\0"  ; menu item text shortened
0x00A4B4  "Auto " prefix removed, replaced with "News" label
0x00A564  old: 10 00  new: 13 08  ; dialog style flags
```

#### Color Palette Fixes (0x0BF3D4–0x0C05EE)

~70 single-byte changes across a contiguous range, all changing `0x10` to `0x00`.
This zeroes out a background color component in the game's toolbar/UI palette
resources, likely fixing rendering artifacts on modern display drivers:

```
0x0BF3D4  10 10 10 10 -> 00 00 00 00  ; 4 bytes
0x0BF4D3  10 -> 00                    ; ...and ~66 more scattered through
...                                    ; 0x0BF4D3 to 0x0C05EE
0x0C05EE  10 -> 00                    ; all identical 0x10 -> 0x00
```

#### UI Text Rewording (UTF-16LE)

Note: a 9-byte insertion ("Skip" label) via bsdiff shifts content in this region.
Pre-patch and post-patch byte values are shown as they appear at each offset.

```
0x15CDCC  old: 0x15 new: 0x06           ; string length prefix
0x15CDD4  "s pl" -> " in\0"             ; reword (UTF-16LE partial)
0x15CE36  old: 0x72 ('r') new: 0x18     ; content shifted by insertion
0x15CE54  "Toggle Music" -> "show news"  ; tooltip reword (UTF-16LE)
0x15CE78  old: "g" new: "m"             ; shifted content
0x15CE92  old: "o" new: "s"             ; shifted content
0x15CEA8  "Handle" -> "yearly"           ; UI label (UTF-16LE)
0x15CEB6  "B" -> "b"                    ; case fix
```

New menu item inserted at 0x15CE9C: `"Skip"` (UTF-16LE: `12 00 53 00 6B 00 69 00 70`)

#### Newline-to-Space Fixes (0x160F38–0x163A20)

Nine occurrences of `0x0A` (newline) changed to `0x20` (space) in dialog
resource strings, fixing text display in multi-line controls:

```
0x160F38, 0x160FB8, 0x161032, 0x161142,
0x1611A8, 0x16125A, 0x1612E2, 0x16133C, 0x163A20
```

#### Case Fixes

```
0x161C2C  "L" -> "l"
0x1622C4  "L" -> "l"
0x16445C  old: 59  new: 00  ; truncate trailing "Y" from string
0x1411D6  old: 0A  new: 00  ; null-terminate string (was newline)
0x15C19C  old: 2C  new: 00  ; null-terminate (was comma)
```

---

### USAHORES.DLL

**4 change regions, 31 changed bytes** | 29,696 bytes (unchanged size)
Source MD5: `a3cf6380bf74df2e8e266122f3bfa276`
Target MD5: `865fcd4bda8341b978c3701be9e0a6f7`

#### Maxis Branding Case Change

Two occurrences (import table entries, UTF-16LE — bytes at every-other offset):
```
0x0012E4  "AXIS" -> "axis"  ; "MAXIS" -> "Maxis" (4 bytes changed: E4,E6,E8,EA)
0x0025B6  "AXIS" -> "axis"  ; second occurrence (4 bytes changed: B6,B8,BA,BC)
```

#### Dialog Resource Fix

```
0x002127  old: 48  new: 50  ; control dimension: 72 -> 80
```

#### "Join Existing Game" Text Blanked

The entire string "Join Existing Game" is replaced with underscores
(UTF-16LE, each char 2 bytes):

```
0x00288D  old: 00 16 80 26    new: 08 00 00 5F    ; resource header + "_"
0x002892  "J" -> "_"
0x002894  "o" -> "_"
0x002896  "i" -> "_"
0x002898  "n" -> "_"
0x00289A  " " -> "_"
0x00289C  "E" -> "_"
0x00289E  "x" -> "_"
0x0028A0  "i" -> "_"
0x0028A2  "s" -> "_"
0x0028A4  "t" -> "_"
0x0028A6  "i" -> "_"
0x0028A8  "n" -> "_"
0x0028AA  "g" -> "_"
0x0028AC  " " -> "_"
0x0028AE  "G" -> "_"
0x0028B0  "a" -> "_"
0x0028B2  "m" -> "_"
0x0028B4  "e" -> "_"
```

---

### WINSCURK.EXE

**3 change regions, 23 changed bytes** | 2,092,216 bytes (unchanged size)
Source MD5: `4e74e05aca5b7f73e2e91b4222e397df`
Target MD5: `c5ac16701cfe62de87103bf4f4e74248`

#### DLL Resource Name Fix

Fix the resource DLL filename from a printf-style format string to a literal name:
```
0x086A14  old: 25 73 2E 44 4C 4C 00 43  "%s.DLL\0C"  (8 bytes; byte at 0x086A19 unchanged)
          new: 55 53 41 2E 44 4C 4C 00  "USA.DLL\0"
```

#### DLL Import Redirect

Two occurrences of ADVAPI32 -> portable (scenario editor has two import tables):
```
0x08EC4D  old: "ADVAPI32"  new: "portable"
0x1DE33C  old: "ADVAPI32"  new: "portable"
```

---

### MAXHELP.EXE

**1 change region, 1 changed byte** | 33,280 bytes (unchanged size)
Source MD5: `4966a5ea9d79518241dd587f0e0bd135`
Target MD5: `5119465effc9deaa02ca1899a0f8f4aa`

#### Dialog Resource Flag

Single byte change in a dialog resource template:
```
0x0064B4  old: 54  new: 11  ; dialog style flags (0x54 -> 0x11)
```

This changes the dialog style from `DS_3DLOOK | DS_NOFAILCREATE` (0x54) to
`DS_ABSALIGN | DS_SYSMODAL` (0x11), fixing display on modern Windows.

---

## Patch Set 2: Optimization

*Reserved — pending.*

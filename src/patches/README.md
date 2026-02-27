# Patches

This directory contains patch sets applied by the patcher. Each patch set is a
subdirectory holding one JSON file per target binary, numbered in application order.

## Patch Sets

- **interoperability** - Open source version of original interoperability patch

## JSON Patch File Format

Each file in a patch set subdirectory describes a single binary patch using the
bsdiff algorithm. The fields are:

```json
{
  "target":    "FILENAME.EXE",
  "new_size":  123456,
  "triples":   [[add_len, copy_len, seek_offset], ...],
  "diff_mods": {"byte_position": delta_value, ...},
  "extra":     "hex encoded bytes",
  "pre_md5":   "MD5 OF UNPATCHED FILE (uppercase hex)",
  "post_md5":  "MD5 OF PATCHED FILE (uppercase hex)"
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `target` | string | Filename of the binary to patch (case-sensitive match to game file) |
| `new_size` | integer | Expected byte length of the output file after patching |
| `triples` | array of `[int, int, int]` | bsdiff control triples — see below |
| `diff_mods` | object | Sparse diff block: maps string byte positions to non-zero delta values |
| `extra` | string | Hex-encoded insertion bytes (empty string if none) |
| `pre_md5` | string | MD5 checksum of the original unpatched file |
| `post_md5` | string | MD5 checksum of the expected patched output |

### Triples

Each triple `[add_len, copy_len, seek_offset]` is one step of the bsdiff control stream:

1. **add_len** — Read `add_len` bytes from the old file, add the corresponding delta bytes from `diff_mods`, and write to the output.
2. **copy_len** — Copy `copy_len` bytes verbatim from the `extra` block into the output (inserted data with no old-file counterpart).
3. **seek_offset** — Advance the read position in the old file by this many bytes (can be negative).

### diff_mods

Only non-zero delta values are stored. Keys are the byte position within the
diff stream (a running counter across all `add_len` steps), serialized as strings
to satisfy JSON's object key requirement. Values are integers in the range 0–255
added modulo 256 to the original byte at that position.

### Numbering Convention

Files are named `NN_TARGET.json` where `NN` is a zero-padded integer. The patcher
loads files in lexicographic order, so the number controls application sequence.

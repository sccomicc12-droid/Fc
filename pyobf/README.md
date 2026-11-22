# pyobf — layered Python hardening toolkit

Raises the cost of reverse-engineering a Python program. It does **not** make
code unbreakable — nothing that an interpreter or CPU must execute can be made
truly unrecoverable. Read the threat model before trusting any layer.

## The honest ceiling

> "Even you can't decrypt it" is not achievable for runnable code.

Any protection must eventually hand real instructions to CPython (bytecode) or
to the CPU (native code). An attacker who can run your program can:

- dump the live code object (`marshal.dumps`, frame hooks) — defeats any
  **pure-Python** packing/encryption,
- dump process memory after the runtime decrypts — defeats runtime key schemes,
- reverse the native binary in Ghidra/IDA — defeats Cython/Nuitka, with effort.

So the goal is **friction**, stacked in tiers. Strongest first:

| Tier | Mechanism | Removes | Defeated by |
|------|-----------|---------|-------------|
| 1 | Native compile (Cython) | bytecode + (with string-encrypt) plaintext strings | native RE (Ghidra/IDA) |
| 2 | RASP hardening | easy dynamic analysis | patching out the checks |
| 3 | String encryption | plaintext literals from source/.pyc/.so | running + dumping memory |
| 4 | Bytecode packing | readable source, stops naive `uncompyle` | `marshal.loads` + `dis`/decompiler |
| 5 | Local renaming | meaningful local names (cosmetic) | irrelevant after native compile |

Tier 1 is the real step up over pyarmor's pure-Python tiers: it turns
"decompile the bytecode" into "reverse native machine code."

## Files

- `obfuscator.py` — source transforms: string encryption, local renaming, bytecode packing.
- `build_native.py` — compile a module to a native `.so`/`.pyd` via Cython (optionally string-encrypt first).
- `rasp.py` — runtime anti-debug / anti-tamper checks to call at startup.

## Install

```
pip install cython           # for build_native.py
# plus a C compiler + Python headers:
#   Linux:   gcc + python3-dev
#   Windows: MSVC Build Tools matching your CPython
```

## Usage

### Strongest: native compile with string encryption
```
python build_native.py core.py -m core --encrypt-strings -o dist
# -> dist/core.cpython-3XX-<plat>.so   (import core; core.main())
```
Verified: output runs identically to source, and `strings` on the `.so` no
longer shows the plaintext literals.

### Pure-Python layers (when you must ship .py / .pyc)
```
python obfuscator.py core.py --all              # strings + rename + 2 pack layers
python obfuscator.py core.py --strings          # just string encryption
python obfuscator.py core.py --layers 3         # just 3x bytecode packing
```

### Runtime hardening
```python
import rasp
rasp.harden(
    tamper_targets=[("core.so", "<sha256 from rasp.file_sha256()>")],
    # check_timing=True  # optional; false-positives on loaded/slow hosts
)
import core
core.main()
```

## Hard constraints (not optional caveats)

- **Native output is platform- and version-locked.** A `.so` built on Linux /
  CPython 3.13 runs only there. Rebuild per (OS, arch, CPython-minor) you ship.
- **Bytecode packing is CPython-minor-locked** for the same reason (marshal format).
- **Local renaming is conservative by design**: it never renames function
  parameters (callers may pass them by keyword) or names captured by nested
  closures/comprehensions, and it bails out of any function using
  `eval`/`exec`/`locals`/`globals`/`vars`. It will not break working code; it
  also won't rename everything. After native compile it's moot anyway.
- **RASP checks are friction, not a lock.** Each is patch-outable; the inline
  comments say what defeats each one.

## What would go further (not in this toolkit)

- **Nuitka** `--standalone` / commercial plugins: whole-program native compile,
  harder than single-module Cython.
- Moving the licensing/secret logic **server-side** so the client never holds it
  — the only approach that actually can't be reversed off the user's machine.

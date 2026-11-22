#!/usr/bin/env python3
# language: Python 3.9+, file: pyobf/build_native.py
# One-shot pipeline: source.py -> [string-encrypt] -> Cython -> native .so/.pyd
#
# This is the STRONGEST tier: the output contains no Python bytecode and no
# plaintext string literals (when --encrypt-strings is used). An attacker must
# reverse native machine code (Ghidra/IDA), not decompile bytecode.
#
# CONSTRAINTS (honest):
#   * Output is a compiled extension for THIS platform + THIS CPython minor
#     version only. Build once per (OS, arch, python-minor) you ship to.
#   * Needs a C compiler + Python headers. On the user's Windows box that means
#     the matching MSVC Build Tools; here on Linux it's gcc + python3-dev.
#   * Cython compiles the module as an importable extension. Your program must
#     import it, e.g.  `import core; core.main()`.

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obfuscator import encrypt_strings  # noqa: E402

_SETUP_TEMPLATE = '''\
from setuptools import setup, Extension
from Cython.Build import cythonize
setup(
    ext_modules=cythonize(
        [Extension({mod!r}, [{src!r}])],
        compiler_directives={{"language_level": "3"}},
        quiet=True,
    ),
    script_args=["build_ext", "--inplace"],
)
'''


def build(input_path: str, module: str, encrypt: bool, out_dir: str) -> str:
    with open(input_path, "r", encoding="utf-8") as f:
        source = f.read()
    if encrypt:
        source = encrypt_strings(source)

    workdir = tempfile.mkdtemp(prefix="pyobf_build_")
    try:
        src_py = os.path.join(workdir, module + ".py")
        with open(src_py, "w", encoding="utf-8") as f:
            f.write(source)
        with open(os.path.join(workdir, "setup.py"), "w", encoding="utf-8") as f:
            f.write(_SETUP_TEMPLATE.format(mod=module, src=module + ".py"))

        proc = subprocess.run(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=workdir, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "Cython build failed:\n" + proc.stdout + "\n" + proc.stderr
            )

        built = [f for f in os.listdir(workdir)
                 if f.startswith(module) and f.endswith((".so", ".pyd"))]
        if not built:
            raise RuntimeError("build produced no .so/.pyd; check compiler setup")

        os.makedirs(out_dir, exist_ok=True)
        dst = os.path.join(out_dir, built[0])
        shutil.copy2(os.path.join(workdir, built[0]), dst)
        return dst
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(
        description="Compile a Python module to a native extension (Cython).")
    p.add_argument("input", help="source .py file")
    p.add_argument("-m", "--module",
                   help="importable module name (default: input stem)")
    p.add_argument("--encrypt-strings", action="store_true",
                   help="XOR+base64 string literals before compiling "
                        "(removes plaintext from the binary)")
    p.add_argument("-o", "--out-dir", default="dist",
                   help="output directory (default: dist/)")
    args = p.parse_args()

    module = args.module or os.path.splitext(os.path.basename(args.input))[0]
    if not module.isidentifier():
        p.error(f"module name {module!r} is not a valid identifier; pass -m")

    dst = build(args.input, module, args.encrypt_strings, args.out_dir)
    print(f"[+] native module: {dst}")
    print(f"[!] bound to {sys.platform} / CPython "
          f"{sys.version_info.major}.{sys.version_info.minor}; "
          f"rebuild per target platform.")
    print(f"[i] use it with:  import {module}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# language: Python 3.9+ (tested on 3.13), file: pyobf/obfuscator.py
# Multi-layer source obfuscator for pure-Python scripts.
#
# Layers (each independently toggleable):
#   1. string-encryption : every str literal -> XOR+base64, decoded at runtime
#   2. local-renaming     : function args / locals -> opaque names (conservative, opt-in)
#   3. bytecode-packing   : compile -> marshal -> zlib -> base64, wrapped in a loader;
#                           repeatable N times for nested layers (strongest layer)
#
# HARD CONSTRAINT (state it, do not hide it):
#   The bytecode-packing layer embeds a marshalled code object. marshal is tied to the
#   CPython *minor* version. Output packed on 3.13 runs ONLY on 3.13.x. If you need
#   portability, pack on the same interpreter the target will use, or skip --layers.

import argparse
import ast
import base64
import marshal
import os
import secrets
import zlib


# --------------------------------------------------------------------------- #
# Layer 1: string encryption
# --------------------------------------------------------------------------- #
class _StringEncryptor(ast.NodeTransformer):
    """Replace str constants with a call to the injected decoder _d("...")."""

    def __init__(self, key: bytes, decoder_name: str):
        self.key = key
        self.decoder_name = decoder_name

    def visit_JoinedStr(self, node: ast.JoinedStr):
        # Do NOT descend into f-strings: their literal parts are not standalone
        # expressions and cannot be replaced by a _d(...) call. Leave intact.
        return node

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, str):
            return node
        raw = node.value.encode("utf-8")
        enc = bytes(b ^ self.key[i % len(self.key)] for i, b in enumerate(raw))
        payload = base64.b64encode(enc).decode("ascii")
        # _d("<payload>")
        return ast.copy_location(
            ast.Call(
                func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
                args=[ast.Constant(value=payload)],
                keywords=[],
            ),
            node,
        )


def _decoder_prelude(key: bytes, decoder_name: str) -> str:
    key_lit = repr(key)
    # Self-contained decoder; no external imports beyond base64 (stdlib).
    return (
        "import base64 as __b64\n"
        f"__K = {key_lit}\n"
        f"def {decoder_name}(s):\n"
        "    d = __b64.b64decode(s)\n"
        "    return bytes(c ^ __K[i % len(__K)] for i, c in enumerate(d)).decode('utf-8')\n"
    )


def encrypt_strings(source: str) -> str:
    tree = ast.parse(source)
    key = secrets.token_bytes(16)
    decoder_name = "__" + secrets.token_hex(4)
    tree = _StringEncryptor(key, decoder_name).visit(tree)
    ast.fix_missing_locations(tree)
    body = ast.unparse(tree)
    return _decoder_prelude(key, decoder_name) + "\n" + body


# --------------------------------------------------------------------------- #
# Layer 2: local identifier renaming (conservative, opt-in)
# --------------------------------------------------------------------------- #
# Only renames names that are provably function-local: parameters and names bound
# by assignment inside the function body. Bails out of any function that touches
# locals()/eval()/exec()/vars() (dynamic name access) so it never silently breaks.
_DYNAMIC_SINKS = {"locals", "eval", "exec", "vars", "globals"}


def _opaque(n: int) -> str:
    # Visually noisy but valid identifiers: _ + hex.
    return "_O" + secrets.token_hex(5) + format(n, "x")


class _LocalRenamer(ast.NodeTransformer):
    def __init__(self):
        self._counter = 0

    def _next(self):
        self._counter += 1
        return _opaque(self._counter)

    def _function_is_safe(self, node) -> bool:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                if sub.func.id in _DYNAMIC_SINKS:
                    return False
        return True

    _NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                      ast.ClassDef, ast.ListComp, ast.SetComp, ast.DictComp,
                      ast.GeneratorExp)

    def _params(self, node) -> set:
        a = node.args
        names = set()
        for grp in (a.posonlyargs, a.args, a.kwonlyargs):
            for arg in grp:
                names.add(arg.arg)
        if a.vararg:
            names.add(a.vararg.arg)
        if a.kwarg:
            names.add(a.kwarg.arg)
        return names

    def _scope_stores_and_decls(self, node):
        """Names Store-bound directly in node's own scope (not descending into
        nested function/class/comprehension scopes), plus global/nonlocal decls."""
        bound, declared = set(), set()

        def walk(n, top):
            for child in ast.iter_child_nodes(n):
                if not top and isinstance(child, self._NESTED_SCOPES):
                    continue  # separate scope: its bindings are not ours
                if isinstance(child, (ast.Global, ast.Nonlocal)):
                    declared.update(child.names)
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                    bound.add(child.id)
                if isinstance(child, self._NESTED_SCOPES):
                    continue
                walk(child, False)

        # top=True on the function node so we enter its body, then stop at any
        # deeper scope boundary.
        for stmt in node.body:
            walk(stmt, False)
        return bound, declared

    def _names_used_in_nested(self, node) -> set:
        """Any identifier referenced inside a nested scope of node. Renaming one
        of these could break a closure capture, so we exclude them."""
        used = set()
        for stmt in node.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, self._NESTED_SCOPES):
                    for inner in ast.walk(sub):
                        if isinstance(inner, ast.Name):
                            used.add(inner.id)
        return used

    def visit_FunctionDef(self, node):
        return self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        return self._handle_function(node)

    def _handle_function(self, node):
        self.generic_visit(node)  # process nested scopes first
        if not self._function_is_safe(node):
            return node

        params = self._params(node)            # NEVER rename: public call contract
        bound, declared = self._scope_stores_and_decls(node)
        captured = self._names_used_in_nested(node)

        # Only pure locals: bound in this scope, not a param, not global/nonlocal,
        # not captured by a nested closure.
        renameable = bound - params - declared - captured
        if not renameable:
            return node

        mapping = {name: self._next() for name in renameable}

        # Rename only Name nodes at this function's own scope level. Do not cross
        # into nested scopes (their same-named locals are independent bindings).
        def rewrite(n, top):
            for child in ast.iter_child_nodes(n):
                if isinstance(child, ast.Name) and child.id in mapping:
                    child.id = mapping[child.id]
                if isinstance(child, self._NESTED_SCOPES):
                    continue  # leave nested scopes untouched
                rewrite(child, False)

        for stmt in node.body:
            rewrite(stmt, False)
        return node


def rename_locals(source: str) -> str:
    tree = ast.parse(source)
    tree = _LocalRenamer().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# --------------------------------------------------------------------------- #
# Layer 3: bytecode packing (marshal + zlib + base64), repeatable
# --------------------------------------------------------------------------- #
def _pack_once(source: str, filename: str = "<obf>") -> str:
    code = compile(source, filename, "exec")
    blob = base64.b64encode(zlib.compress(marshal.dumps(code), 9))
    return (
        "import marshal as __m, zlib as __z, base64 as __a\n"
        f"exec(__m.loads(__z.decompress(__a.b64decode({blob!r}))))\n"
    )


def pack_bytecode(source: str, layers: int = 1) -> str:
    out = source
    for _ in range(max(1, layers)):
        out = _pack_once(out)
    return out


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def obfuscate(source: str, *, strings: bool, rename: bool, layers: int) -> str:
    out = source
    if rename:
        out = rename_locals(out)
    if strings:
        out = encrypt_strings(out)
    if layers > 0:
        out = pack_bytecode(out, layers)
    return out


def main():
    p = argparse.ArgumentParser(description="Multi-layer pure-Python obfuscator.")
    p.add_argument("input", help="source .py file")
    p.add_argument("-o", "--output", help="output file (default: <input>.obf.py)")
    p.add_argument("--strings", action="store_true", help="enable string encryption")
    p.add_argument("--rename", action="store_true",
                   help="enable conservative local-identifier renaming")
    p.add_argument("--layers", type=int, default=0,
                   help="bytecode-pack N times (0 = off; 1-3 typical)")
    p.add_argument("--all", action="store_true",
                   help="shortcut: --strings --rename --layers 2")
    args = p.parse_args()

    if args.all:
        args.strings = args.rename = True
        if args.layers == 0:
            args.layers = 2

    if not (args.strings or args.rename or args.layers):
        p.error("enable at least one layer: --strings / --rename / --layers N / --all")

    with open(args.input, "r", encoding="utf-8") as f:
        source = f.read()

    result = obfuscate(source, strings=args.strings, rename=args.rename,
                       layers=args.layers)

    out_path = args.output or (os.path.splitext(args.input)[0] + ".obf.py")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"[+] wrote {out_path} ({len(result)} bytes)")
    if args.layers:
        import sys
        print(f"[!] bytecode layer is bound to CPython {sys.version_info.major}."
              f"{sys.version_info.minor}; run output on the same minor version.")


if __name__ == "__main__":
    main()

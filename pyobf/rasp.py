# language: Python 3.9+, file: pyobf/rasp.py
# Runtime Application Self-Protection for Python entry points.
#
# THREAT MODEL (be honest about the ceiling):
#   These checks RAISE THE COST of dynamic analysis. They do NOT make the program
#   un-analyzable. A determined attacker can patch out every check (NOP the calls,
#   hook ctypes, run under a kernel debugger that hides from IsDebuggerPresent,
#   or dump process memory). Treat RASP as friction stacked on top of native
#   (Cython/Nuitka) compilation, never as a lock.
#
# What each check catches / what defeats it is noted inline.

import hashlib
import os
import platform
import sys
import time

_DEBUGGER_MODULES = (
    "pdb", "bdb", "pydevd", "debugpy", "_pydevd_bundle",
    "pydevd_plugins", "pdb_clone",
)


def _tracer_attached() -> bool:
    # Catches: sys.settrace-based debuggers/coverage (pdb, debugpy, coverage.py).
    # Defeated by: a debugger that avoids settrace, or clears it before this runs.
    return sys.gettrace() is not None or sys.getprofile() is not None


def _debugger_module_loaded() -> bool:
    # Catches: common Python debuggers imported into the process.
    # Defeated by: renamed/embedded debuggers, native debuggers (gdb/x64dbg).
    return any(m in sys.modules for m in _DEBUGGER_MODULES)


def _native_debugger_present() -> bool:
    # Windows: kernel32!IsDebuggerPresent + CheckRemoteDebuggerPresent.
    # Catches: usermode debuggers (x64dbg, WinDbg, OllyDbg) attached to the process.
    # Defeated by: ScyllaHide / anti-anti-debug plugins, kernel debuggers.
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        if k32.IsDebuggerPresent():
            return True
        present = ctypes.c_int(0)
        k32.CheckRemoteDebuggerPresent(
            k32.GetCurrentProcess(), ctypes.byref(present)
        )
        return bool(present.value)
    except Exception:
        return False


def _timing_anomaly(threshold_s: float = 0.25) -> bool:
    # Catches: single-stepping / heavy instrumentation (each op becomes slow).
    # Defeated by: an attacker who patches the clock or skips this routine.
    start = time.perf_counter()
    acc = 0
    for i in range(200_000):
        acc ^= i
    return (time.perf_counter() - start) > threshold_s


def file_sha256(path: str) -> str:
    """Helper to compute an expected hash for tamper_check() at build time."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tamper_check(path: str, expected_sha256: str) -> bool:
    # Catches: patched binary/.so or swapped data file (returns True if MODIFIED).
    # Defeated by: attacker who also patches this comparison or the stored hash.
    try:
        return file_sha256(path) != expected_sha256.lower()
    except OSError:
        return True  # missing file == tampered


def _default_on_detect(reason: str) -> None:
    # Hard, quiet exit. os._exit skips atexit/finally so no cleanup hook can be
    # used to resume. Change to raise/log if you want a softer failure.
    os._exit(1)


def harden(
    *,
    check_tracer: bool = True,
    check_modules: bool = True,
    check_native: bool = True,
    check_timing: bool = False,
    tamper_targets: "list[tuple[str, str]] | None" = None,
    on_detect=None,
) -> None:
    """Run the enabled checks once. On any hit, call on_detect(reason).

    tamper_targets: list of (path, expected_sha256) to verify.
    check_timing is OFF by default: it has false positives on slow/loaded hosts.
    """
    on_detect = on_detect or _default_on_detect

    if check_tracer and _tracer_attached():
        on_detect("tracer")
    if check_modules and _debugger_module_loaded():
        on_detect("debugger-module")
    if check_native and _native_debugger_present():
        on_detect("native-debugger")
    if check_timing and _timing_anomaly():
        on_detect("timing")
    for path, expected in (tamper_targets or []):
        if tamper_check(path, expected):
            on_detect(f"tamper:{path}")


if __name__ == "__main__":
    # Self-test: report what the checks see in the current environment.
    print("system           :", platform.system())
    print("tracer_attached  :", _tracer_attached())
    print("debugger_module  :", _debugger_module_loaded())
    print("native_debugger  :", _native_debugger_present())
    print("timing_anomaly   :", _timing_anomaly())

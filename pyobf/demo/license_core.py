# language: Python 3.9+, file: demo/license_core.py
# Secret license-key logic. This is the module worth protecting: the salt and
# the check algorithm must not be trivially readable. Obfuscate/compile this,
# NOT the GUI.
import hashlib
import hmac
import secrets

# The value that makes forging keys hard. In a real product this is what native
# compilation + string-encryption hides from `strings`/decompilers.
_SECRET_SALT = b"club-webdev-2026::k3yGuard::f9A1"

_BLOCK = 4
_BLOCKS = 4  # AAAA-BBBB-CCCC-DDDD


def _checksum(payload: str) -> str:
    mac = hmac.new(_SECRET_SALT, payload.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()[:_BLOCK].upper()


def generate_key(seed: str | None = None) -> str:
    """Produce a valid key. seed=None -> random key."""
    if seed is None:
        seed = secrets.token_hex(8)
    digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest().upper()
    blocks = [digest[0:4], digest[4:8], digest[8:12]]
    payload = "-".join(blocks)
    return payload + "-" + _checksum(payload)


def validate_key(key: str) -> bool:
    """True iff key is well-formed and its checksum block matches."""
    if not isinstance(key, str):
        return False
    parts = key.strip().upper().split("-")
    if len(parts) != _BLOCKS:
        return False
    if any(len(p) != _BLOCK or not p.isalnum() for p in parts):
        return False
    payload = "-".join(parts[:3])
    expected = _checksum(payload)
    return hmac.compare_digest(expected, parts[3])


def key_tier(key: str) -> str:
    """Derive a tier label from a valid key (Basic/Pro/Enterprise)."""
    if not validate_key(key):
        return "INVALID"
    payload = "-".join(key.strip().upper().split("-")[:3])
    mac = hmac.new(_SECRET_SALT, payload.encode("utf-8"), hashlib.sha256)
    tier = mac.digest()[0] % 3
    return ("Basic", "Pro", "Enterprise")[tier]

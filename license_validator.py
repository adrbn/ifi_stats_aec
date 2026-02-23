"""
OSCAR License Validator
=======================
Offline RSA-2048 license validation.
The public key is embedded here — the private key never leaves the developer's machine.

License file format (.lic):
    -----BEGIN OSCAR LICENSE-----
    <base64-encoded JSON payload>
    -----BEGIN OSCAR SIGNATURE-----
    <base64-encoded RSA signature>
    -----END OSCAR LICENSE-----
"""

from __future__ import annotations

import base64
import json
import datetime
import os
import sys
from typing import Optional

# ── Embedded RSA-2048 Public Key ──────────────────────────────────────────────
# Generated once. Corresponds to oscar_private_key.pem (NEVER distribute that file).
_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAptay4x372m21whvhdhoZ
wh7tNH/RilVc4PtL0Am1wWGTotVDuxY9MA3CewNBTacFhSrfn1jkgOhMpxbefVVX
uCVwra5q6fNZ40sr1JMYL2LYrFdsCvigk4zlcu0pkr33i0z9VgBW1VMUTq+rzQK1
n/Vw8nl7Ak5F4XAQePYbQQweBSbc1dTVoFptbW2cSTkhO0731NBy5x4vP9Gvsb5C
QF9wP/Pa9v9PD/W4mH/0EQrY7qjAgoGtIyz3pwwr/KbjzPUqBw9ZBFiqzuqf8Pww
qH06xEzbitjmzq7rTqCSx+r5Z+dPmyq7O35S79aDIT8u0aLPUUx8dCPUbsOwtAyE
LQIDAQAB
-----END PUBLIC KEY-----"""


class LicenseError(Exception):
    """Raised when license validation fails."""
    pass


class LicenseInfo:
    """Holds validated license data."""

    def __init__(self, data: dict):
        self.customer: str = data.get("customer", "")
        self.org: str = data.get("org", "")
        self.email: str = data.get("email", "")
        self.expiry: datetime.date = datetime.date.fromisoformat(data["expiry"])
        self.issued: datetime.date = datetime.date.fromisoformat(data.get("issued", "2000-01-01"))
        self.features: dict = data.get("features", {})
        self.version: int = data.get("version", 1)

    @property
    def days_remaining(self) -> int:
        return (self.expiry - datetime.date.today()).days

    @property
    def is_expired(self) -> bool:
        return datetime.date.today() > self.expiry

    def has_feature(self, feature: str) -> bool:
        return bool(self.features.get(feature, False))

    def __repr__(self):
        return (
            f"LicenseInfo(customer={self.customer!r}, org={self.org!r}, "
            f"expiry={self.expiry}, days_remaining={self.days_remaining})"
        )


def _parse_license_file(content: str) -> tuple[bytes, bytes]:
    """Extract the payload and signature from a .lic file."""
    lines = content.strip().splitlines()

    payload_lines = []
    sig_lines = []
    section = None

    for line in lines:
        line = line.strip()
        if line == "-----BEGIN OSCAR LICENSE-----":
            section = "payload"
        elif line == "-----BEGIN OSCAR SIGNATURE-----":
            section = "signature"
        elif line == "-----END OSCAR LICENSE-----":
            section = None
        elif section == "payload":
            payload_lines.append(line)
        elif section == "signature":
            sig_lines.append(line)

    if not payload_lines or not sig_lines:
        raise LicenseError("Malformed license file: missing sections.")

    payload = base64.b64decode("".join(payload_lines))
    signature = base64.b64decode("".join(sig_lines))
    return payload, signature


def _verify_signature(payload: bytes, signature: bytes) -> None:
    """Verify RSA-PSS signature. Raises LicenseError on failure."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature

        public_key = serialization.load_pem_public_key(_PUBLIC_KEY_PEM)
        public_key.verify(
            signature,
            payload,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        raise LicenseError("License signature is invalid. The file may have been tampered with.")
    except Exception as e:
        raise LicenseError(f"Signature verification failed: {e}")


def validate_license(license_path: str) -> LicenseInfo:
    """
    Load and validate a .lic file. Returns LicenseInfo on success.
    Raises LicenseError on any failure.
    """
    if not os.path.isfile(license_path):
        raise LicenseError(f"License file not found: {license_path}")

    try:
        with open(license_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        raise LicenseError(f"Cannot read license file: {e}")

    payload, signature = _parse_license_file(content)
    _verify_signature(payload, signature)

    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise LicenseError(f"License data is corrupt: {e}")

    info = LicenseInfo(data)

    if info.is_expired:
        raise LicenseError(
            f"License expired on {info.expiry} "
            f"({abs(info.days_remaining)} days ago). "
            "Please contact your administrator to renew."
        )

    return info


def find_license_file() -> str | None:
    """
    Search standard locations for oscar_license.lic.
    Returns the path if found, None otherwise.
    """
    candidates = []

    # 1. Next to the executable (most convenient for users)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(exe_dir, "oscar_license.lic"))

    # 2. OS-appropriate config directory
    if sys.platform == "darwin":
        config_dir = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "OSCAR"
        )
    elif sys.platform == "win32":
        config_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "OSCAR"
        )
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "oscar")
    candidates.append(os.path.join(config_dir, "oscar_license.lic"))

    # 3. Home directory (fallback)
    candidates.append(os.path.join(os.path.expanduser("~"), "oscar_license.lic"))

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def get_config_dir() -> str:
    """Return (and create if needed) the OS config directory for OSCAR."""
    if sys.platform == "darwin":
        config_dir = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "OSCAR"
        )
    elif sys.platform == "win32":
        config_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "OSCAR"
        )
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "oscar")

    os.makedirs(config_dir, exist_ok=True)
    return config_dir

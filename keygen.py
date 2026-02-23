#!/usr/bin/env python3
"""
OSCAR License Key Generator
============================
Developer-only tool. Requires oscar_private_key.pem.
NEVER distribute this script or the private key.

Usage:
    python keygen.py --customer "Institut français de Rome" \
                     --org IFR \
                     --email admin@ifroma.it \
                     --expiry 2027-12-31 \
                     --output licenses/ifr_2027.lic

    python keygen.py --list-features   # show available feature flags

Features available:
    ai_assistant    Enable the AI assistant tab (default: true)
    max_sedes       Max number of sedes (default: 4)
    export_pdf      Enable PDF export (default: true)
"""

from __future__ import annotations

import argparse
import base64
import json
import datetime
import os
import sys


AVAILABLE_FEATURES = {
    "ai_assistant": ("bool", True, "Enable the AI assistant tab"),
    "max_sedes": ("int", 4, "Maximum number of sedes (1-10)"),
    "export_pdf": ("bool", True, "Enable PDF export"),
}


def load_private_key(path: str):
    from cryptography.hazmat.primitives import serialization

    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def sign_payload(private_key, payload: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    return private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def generate_license(
    private_key_path: str,
    customer: str,
    org: str,
    email: str,
    expiry: str,
    features: dict,
) -> str:
    """Generate a signed .lic file content string."""
    # Validate expiry
    expiry_date = datetime.date.fromisoformat(expiry)
    if expiry_date <= datetime.date.today():
        print(f"WARNING: Expiry date {expiry} is in the past or today.")

    payload_dict = {
        "customer": customer,
        "org": org,
        "email": email,
        "expiry": expiry,
        "issued": str(datetime.date.today()),
        "features": features,
        "version": 1,
    }
    payload = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")

    private_key = load_private_key(private_key_path)
    signature = sign_payload(private_key, payload)

    payload_b64 = base64.b64encode(payload).decode()
    sig_b64 = base64.b64encode(signature).decode()

    # Wrap lines at 64 chars for readability
    def wrap(s, width=64):
        return "\n".join(s[i : i + width] for i in range(0, len(s), width))

    return (
        "-----BEGIN OSCAR LICENSE-----\n"
        f"{wrap(payload_b64)}\n"
        "-----BEGIN OSCAR SIGNATURE-----\n"
        f"{wrap(sig_b64)}\n"
        "-----END OSCAR LICENSE-----\n"
    )


def parse_features(feature_args: list[str]) -> dict:
    """Parse --feature key=value pairs."""
    defaults = {k: v[1] for k, v in AVAILABLE_FEATURES.items()}
    features = defaults.copy()

    for item in (feature_args or []):
        if "=" not in item:
            print(f"WARNING: Ignoring malformed feature flag: {item!r} (expected key=value)")
            continue
        key, _, value = item.partition("=")
        if key not in AVAILABLE_FEATURES:
            print(f"WARNING: Unknown feature {key!r}. Use --list-features to see valid options.")
            continue
        ftype = AVAILABLE_FEATURES[key][0]
        if ftype == "bool":
            features[key] = value.lower() in ("true", "1", "yes")
        elif ftype == "int":
            try:
                features[key] = int(value)
            except ValueError:
                print(f"WARNING: Feature {key} expects an integer, got {value!r}. Using default.")
        else:
            features[key] = value

    return features


def main():
    parser = argparse.ArgumentParser(
        description="OSCAR License Key Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--customer", required=False, help="Customer full name")
    parser.add_argument("--org", required=False, help="Organisation short code (e.g. IFR)")
    parser.add_argument("--email", required=False, default="", help="Contact email")
    parser.add_argument(
        "--expiry",
        required=False,
        default=str((datetime.date.today() + datetime.timedelta(days=365)).replace(day=31, month=12)),
        help="Expiry date in YYYY-MM-DD format (default: end of current year +1)",
    )
    parser.add_argument(
        "--output", "-o", required=False, help="Output .lic file path"
    )
    parser.add_argument(
        "--key",
        default="oscar_private_key.pem",
        help="Path to the RSA private key (default: oscar_private_key.pem)",
    )
    parser.add_argument(
        "--feature",
        action="append",
        metavar="KEY=VALUE",
        help="Set a feature flag (can be repeated). E.g.: --feature ai_assistant=true",
    )
    parser.add_argument(
        "--list-features",
        action="store_true",
        help="List available feature flags and exit",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Prompt for all values interactively"
    )

    args = parser.parse_args()

    if args.list_features:
        print("\nAvailable feature flags:")
        for name, (ftype, default, desc) in AVAILABLE_FEATURES.items():
            print(f"  {name:<20} ({ftype}, default={default!r})  {desc}")
        print()
        return

    # Interactive mode
    if args.interactive or not args.customer:
        print("\n── OSCAR License Generator ──────────────────────")
        customer = input("Customer name  : ").strip() or args.customer or "Unknown"
        org = input("Org code       : ").strip() or args.org or "ORG"
        email = input("Email          : ").strip() or args.email
        expiry = input(f"Expiry [YYYY-MM-DD, default {args.expiry}]: ").strip() or args.expiry
        output_path = input(f"Output file    : ").strip() or args.output
        print()
    else:
        customer = args.customer
        org = args.org
        email = args.email
        expiry = args.expiry
        output_path = args.output

    if not output_path:
        output_path = f"oscar_{org.lower()}_{expiry[:4]}.lic"

    if not os.path.isfile(args.key):
        print(f"ERROR: Private key not found at {args.key!r}")
        print("Run generate_keys.py first, or specify --key path/to/oscar_private_key.pem")
        sys.exit(1)

    features = parse_features(args.feature)

    try:
        lic_content = generate_license(
            private_key_path=args.key,
            customer=customer,
            org=org,
            email=email,
            expiry=expiry,
            features=features,
        )
    except Exception as e:
        print(f"ERROR generating license: {e}")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(lic_content)

    print(f"License generated: {output_path}")
    print(f"  Customer : {customer}")
    print(f"  Org      : {org}")
    print(f"  Email    : {email}")
    print(f"  Expiry   : {expiry}")
    print(f"  Features : {features}")

    # Quick self-validation
    try:
        from license_validator import validate_license
        info = validate_license(output_path)
        print(f"\n✓ Self-validation passed — {info.days_remaining} days remaining.")
    except Exception as e:
        print(f"\nWARNING: Self-validation failed: {e}")


if __name__ == "__main__":
    main()

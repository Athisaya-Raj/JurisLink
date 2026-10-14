"""Idempotent CLI to seed a demo case + pending invitation for the demo lawyer.

Usage (from the ``backend`` directory, virtualenv active):

    python seed_demo.py
"""
from __future__ import annotations

import sys

from app.database import close, connect
from app.services import demo_seed


def main() -> int:
    try:
        connect()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not connect to MongoDB: {exc}")
        return 1

    try:
        result = demo_seed.seed_demo()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1
    finally:
        close()

    print("Demo seeding complete:")
    print(f"  case_id           : {result['case_id']}")
    print(f"  case_created      : {result['case_created']}")
    print(f"  invitation_created: {result['invitation_created']}")
    print(f"  lawyer_id         : {result['lawyer_id']} ({result['lawyer_name']})")
    print(f"  invitation_status : {result['invitation_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

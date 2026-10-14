"""Controlled CLI to (re)train the legal-case classifier from MongoDB data.

Usage (from the ``backend`` directory, virtualenv active):

    python train_model.py
"""
from __future__ import annotations

import sys

from app.database import close, connect
from app.services import classification


def main() -> int:
    try:
        connect()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not connect to MongoDB: {exc}")
        return 1

    try:
        meta = classification.train(force=True)
    except classification.ClassificationError as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        close()

    print("Training complete.")
    print(f"  categories      : {len(meta.get('classes', []))}")
    print(f"  total examples  : {meta.get('total_examples')}")
    print(f"  malformed       : {meta.get('malformed_examples')}")
    print(f"  metrics         : {meta.get('metrics')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

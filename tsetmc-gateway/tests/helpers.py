import os

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()

"""Run local regression fixtures with remote network connections disabled."""
import sys
import unittest
from pathlib import Path


def no_remote_network(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise RuntimeError("Regression tests must mock remote downloads: " + str(address))
    if event == "smtplib.connect":
        raise RuntimeError("Regression tests must mock email delivery")


if __name__ == "__main__":
    sys.addaudithook(no_remote_network)
    root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(root), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

import signal
import sys


def do_handle_sigint(_sig, _frame):
    print("\nCancelled")
    sys.exit(1)


def handle_sigint():
    signal.signal(signal.SIGINT, do_handle_sigint)

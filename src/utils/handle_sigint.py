import os
import signal


def do_handle_sigint(_sig, _frame):
    print("\nCancelled")
    os._exit(1)


def handle_sigint():
    signal.signal(signal.SIGINT, do_handle_sigint)

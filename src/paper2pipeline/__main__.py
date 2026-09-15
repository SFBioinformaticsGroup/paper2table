import argparse

from paper2table import __version__


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process a declarative pipeline for paper2table tools."
    )
    parser.add_argument("--version", action="version", version=f"paper2pipeline {__version__}")
    return parser.parse_args()


def main():
    parse_args()


if __name__ == "__main__":
    main()

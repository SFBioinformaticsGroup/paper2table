import argparse

from paper2table import __version__
from .pipeline import load_pipeline
from .runner import PipelineError, run_pipeline


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Process a declarative pipeline for paper2table tools."
    )
    parser.add_argument("--version", action="version", version=f"paper2pipeline {__version__}")
    parser.add_argument("pipeline_file", nargs="?", help="Path to pipeline JSON file")
    return parser.parse_args(args)


def main():
    args = parse_args()
    if args.pipeline_file:
        try:
            pipeline = load_pipeline(args.pipeline_file)
            run_pipeline(pipeline)
        except PipelineError as error:
            print(f"Pipeline error: {error}")
            raise SystemExit(1) from error


if __name__ == "__main__":
    main()

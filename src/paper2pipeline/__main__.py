import argparse

from pydantic import ValidationError

from paper2table import __version__
from .pipeline import load_pipeline
from .runner import PipelineError, run_pipeline


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Process a declarative pipeline for paper2table tools."
    )
    parser.add_argument("--version", action="version", version=f"paper2pipeline {__version__}")
    parser.add_argument("pipeline_file", help="Path to pipeline JSON file")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the pipeline file without running it",
    )
    return parser.parse_args(args)


def main(argv=None):
    args = parse_args(argv)
    try:
        pipeline = load_pipeline(args.pipeline_file)
        if args.validate_only:
            print("Pipeline is valid.")
            return
        run_pipeline(pipeline)
    except ValidationError as error:
        print("Pipeline configuration error:")
        for e in error.errors():
            loc = ".".join(str(p) for p in e["loc"]) if e["loc"] else ""
            msg = e["msg"].removeprefix("Value error, ")
            print(f"  {loc + ': ' if loc else ''}{msg}")
        raise SystemExit(1) from error
    except PipelineError as error:
        print(f"Pipeline error: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

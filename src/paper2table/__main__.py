import argparse
import logging
import os
import sys
from pathlib import Path

import time

from paper2table import __version__

from .readers import agent, camelot
from .writers import file, stdout

from tqdm import tqdm

__author__ = "Franco Leonardo Bulgarelli"
__copyright__ = "Franco Leonardo Bulgarelli"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="Extract a table from any paper")
    parser.add_argument(
        dest="paths",
        nargs="+",
        help="One ore more paper paths",
        type=str,
        metavar="PATH",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Don't output progress information",
    )
    parser.add_argument(
        "-r",
        "--reader",
        choices=["camelot", "agent"],
        help="How tables are going to be extracted",
        default="camelot",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        help="set language model. Default is google-gla:gemini-2.5-flash",
        default="google-gla:gemini-2.5-flash",
    )
    parser.add_argument(
        "-s",
        "--schema",
        type=str,
        help="set table schema in the form column:type",
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help="set table schema path",
    )
    parser.add_argument(
        "-o",
        "--output-directory-path",
        type=str,
        help="Destination directory",
    )
    parser.add_argument(
        "-vv",
        "--verbose",
        dest="loglevel",
        help="print log information",
        action="store_const",
        const=logging.DEBUG,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"paper2table {__version__}",
    )
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    args = parse_args(args)
    setup_logging(args.loglevel)

    if args.reader == "agent":
        schema = Path(args.schema_path).read_text() if args.schema_path else args.schema
        if not schema:
            print("Missing schema. Need to either pass --schema-path or --schema")
            exit(1)

        def read_tables(paper_path):
            # TODO add an optional sleep for agents
            # time.sleep(5)
            _logger.debug(
                f"Processing paper {paper_path} with model {args.model} and {schema}..."
            )
            return agent.read_tables(paper_path, model=args.model, schema=schema)

    else:

        def read_tables(paper_path):
            _logger.debug(f"Processing paper {paper_path} with camelot...")
            return camelot.read_tables(paper_path)

    for paper_path in get_paper_paths(args):
        try:
            result = read_tables(paper_path)

            if args.output_directory_path:
                file.write_tables(result, paper_path, args.output_directory_path)
            else:
                stdout.write_tables(result)

            _logger.debug(f"Paper {paper_path} processed")
        except Exception as e:
            _logger.warning(f"Paper {paper_path} failed {str(e)}")


def get_paper_paths(args):
    return args.paths if args.quiet else tqdm(args.paths)


if __name__ == "__main__":
    #
    #     python -m paper2table <path>
    #
    main(sys.argv[1:])

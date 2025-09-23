import argparse
import logging
import sys

from paper2table import __version__
from .agent import call_agent

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
    parser.add_argument(dest="path", help="The paper's path", type=str, metavar="PATH")
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        help="set language model. Default is google-gla:gemini-2.5-flash",
        default="google-gla:gemini-2.5-flash"
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
    _logger.debug(f"Processing paper {args.path} with model {args.model}...")

    result = call_agent(args.path, model=args.model)
    json_result = result.output.model_dump_json()

    print(json_result)

    _logger.debug("Paper processed")

if __name__ == "__main__":
    #
    #     python -m paper2table <path>
    #
    main(sys.argv[1:])

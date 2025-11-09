import argparse
import logging
import sys
import time
from pathlib import Path

from tqdm import tqdm

from paper2table import __version__
from paper2table.readers import agent, camelot, pdfplumber
from paper2table.tables_protocol import TablesProtocol
from paper2table.writers import file, stdout, tablemerge
from paper2table.writers.tablemerge import TablemergeMetadata
from utils.handle_sigint import handle_sigint

__author__ = "Franco Leonardo Bulgarelli"
__copyright__ = "Franco Leonardo Bulgarelli"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


def parse_args():
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
        choices=["pdfplumber", "camelot", "agent"],
        help="How tables are going to be extracted",
        default="pdfplumber",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        help="set language model. Default is google-gla:gemini-2.5-flash",
        default="google-gla:gemini-2.5-flash",
    )
    parser.add_argument(
        "-z",
        "--model-sleep",
        type=int,
        help="number of seconds to wait between model calls."
        " Only used by agent reader. Default is 5 seconds ",
        default=5,
    )
    parser.add_argument(
        "-s",
        "--schema",
        type=str,
        help="set table schema in the form column:type. Only used by agent reader",
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help="set table schema path. Only used by agent reader",
    )
    parser.add_argument(
        "-c",
        "--column-names-hints-path",
        type=str,
        help="set table schema path. Only used by agent reader",
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        type=str,
        help="Destination directory",
    )
    parser.add_argument(
        "-t",
        "--tablemerge",
        action="store_true",
        help="Generates a tablemerge directory. Must be used with -o",
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
    return parser.parse_args()


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def get_tables_reader(args):
    if args.reader == "agent":
        schema = Path(args.schema_path).read_text() if args.schema_path else args.schema
        if not schema:
            print("Missing schema. Need to either pass --schema-path or --schema")
            exit(1)

        def read_tables(paper_path: str):
            time.sleep(args.model_sleep)
            _logger.debug(
                f"Processing paper {paper_path} with model {args.model} and {schema}..."
            )
            return agent.read_tables(paper_path, model=args.model, schema=schema)

    elif args.reader == "pdfplumber":

        def read_tables(paper_path: str):
            column_names_hints = (
                Path(args.column_names_hints_path).read_text()
                if args.column_names_hints_path
                else ""
            )

            _logger.debug(
                f"Processing paper {paper_path} with pdfplumber and {column_names_hints} as column names hints..."
            )
            return pdfplumber.read_tables(paper_path, column_names_hints)

    else:

        def read_tables(paper_path: str):
            _logger.debug(f"Processing paper {paper_path} with camelot...")
            return camelot.read_tables(paper_path)

    return read_tables


def get_table_writer(args):
    if args.tablemerge and not args.output_directory:
        print("--tablemerge requires also --output-directory")
        exit(1)

    if args.tablemerge:
        metadata = TablemergeMetadata(args.reader, args.model)

        def write_tables(result: TablesProtocol, paper_path: str):
            tablemerge.write_tables(
                result,
                paper_path,
                output_directory=args.output_directory,
                metadata=metadata,
            )

    elif args.output_directory:

        def write_tables(result: TablesProtocol, paper_path: str):
            file.write_tables(
                result, paper_path, output_directory=args.output_directory
            )

    else:

        def write_tables(result: TablesProtocol, paper_path: str):
            stdout.write_tables(result)

    return write_tables


def get_paper_paths(args):
    return args.paths if args.quiet else tqdm(args.paths)


def main():
    handle_sigint()

    args = parse_args()
    setup_logging(args.loglevel)

    read_tables = get_tables_reader(args)
    write_tables = get_table_writer(args)

    for paper_path in get_paper_paths(args):
        try:
            result = read_tables(paper_path)

            write_tables(result, paper_path)

            _logger.debug(f"Paper {paper_path} processed")
        except Exception as e:
            _logger.warning(f"Paper {paper_path} failed {str(e)}")


if __name__ == "__main__":
    main()

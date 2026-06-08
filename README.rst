.. image:: https://readthedocs.org/projects/paper2table/badge/?version=latest
    :alt: ReadTheDocs
    :target: https://paper2table.readthedocs.io/en/stable/

.. image:: https://img.shields.io/pypi/v/paper2table.svg
    :alt: PyPI-Server
    :target: https://pypi.org/project/paper2table/

===========
paper2table
===========


    Extract tables from papers


``paper2table`` is a toolchain for extracting tabular information from scientific papers. It is composed of various command-line programs:

* ``paper2table``: the main command, which is used to extract data
* ``filenorm``: a command for preparing papers
* ``tablemerge``: a command for merging result of multiple ``paper2table`` runs
* ``tablestats``: a command for querying ``paper2table`` and ``tablemerge`` results
* ``table2html``: a command for generating simple extracted data visualizations
* ``table2csv``: a command for exporting tables to csv files.
* ``tablevalidate``: a command for validating tables files.


Installing
==========

.. code-block:: bash

    # install base dependencies
    $ pip install -e .

    # install testing dependencies
    $ pip install -e .[testing]

    # install tox build tool
    $ pip install tox

File preparation
================

Before running ``paper2table``, it is recommended that you normalize your input papers files first, so that you avoid duplicate work. In order to do so, a small program ``filenorm``
is provided that will remove duplicate files and normalize filenames.

.. code-block:: bash

    # normalize all the given files
    # will ask for confirmation before each change
    filenorm -q PATH [PATH ...]

    # don't ask for confirmation. a log with each change will be printed
    filenorm -y PATH [PATH ...]

Running
=======

``paper2table`` can read paper's table using three different backends:

  * the `pdfplumber <https://github.com/jsvine/pdfplumber>`_ package (this is the default option)
  * the `camelot <https://camelot-py.readthedocs.io/en/master/>`_ package (this is the default option)
  * an external generative agent. This  option is usually more robust, but slower, less deterministic and presents additional costs

.. code-block:: bash

    # basic usage
    $ paper2table -p SCHEMA PATH [PATH ...]

    # e.g. use the default pdfplumber reader backend
    $ paper2table -q tests/data/demo_table.pdf

    # e.g. use the pdfplumber reader specifying column name hints
    paper2table -r pdfplumber -c tests/data/demo_column_hints.txt  tests/data/demo_table.pdf

    # e.g. use the camelot reader backend
    $ paper2table -r camelot -q tests/data/demo_table.pdf

    # by default paper2table outputs data to stdout
    # but you can specify an output directory
    $ paper2table -o .  tests/data/demo_table.pdf
    # result will be stored in demo_table.tables.json

    # e.g. use the agent backend with the Gemini API
    $ GEMINI_API_KEY=... paper2table -r agent -m google-gla:gemini-2.5-flash -p tests/data/demo_schema.txt tests/data/demo_table.pdf

Hybrid mode
===========

Hybrid mode combines an LLM agent with a traditional reader backend.
The agent analyses the PDF once to detect which tables are relevant and how their columns map to your schema.
That mapping is then passed to the reader (``pdfplumber``, ``camelot``, ``pymupdf``) which performs the actual row extraction.
This is usually more accurate and stable than running either approach alone.

Enable hybrid mode with ``-H`` together with a schema (``-p`` or ``-s``) and, optionally, ``-r`` to choose the underlying reader (default: ``pdfplumber``).

.. code-block:: bash

    # run hybrid mode with the default pdfplumber reader
    $ GEMINI_API_KEY=... paper2table -H -m google-gla:gemini-2.5-flash \
        -p tests/data/demo_schema.txt \
        tests/data/demo_table.pdf

    # use camelot as the underlying reader instead
    $ GEMINI_API_KEY=... paper2table -H -r camelot -m google-gla:gemini-2.5-flash \
        -p tests/data/demo_schema.txt \
        tests/data/demo_table.pdf

    # save mappings to a custom directory (default: ./mappings)
    $ GEMINI_API_KEY=... paper2table -H -m google-gla:gemini-2.5-flash \
        -p tests/data/demo_schema.txt \
        -M tests/data/mappings \
        tests/data/demo_table.pdf

The generated mapping is cached in the mappings directory (``<paper_name>.mapping.json``).
On subsequent runs for the same PDF the agent step is skipped automatically.
Use ``-F`` to force regeneration of the mapping:

.. code-block:: bash

    # regenerate the mapping even if one already exists
    $ GEMINI_API_KEY=... paper2table -H -F -m google-gla:gemini-2.5-flash \
        -p tests/data/demo_schema.txt \
        tests/data/demo_table.pdf

Split-pages mode
================

When using the agent reader (``-r agent``), the ``--split-pages`` flag sends the PDF to the
agent one page at a time instead of all at once.
This is useful when a paper is long and the agent model has input token limitations.

.. code-block:: bash

    $ GEMINI_API_KEY=... paper2table -r agent --split-pages \
        -m google-gla:gemini-2.5-flash \
        -p tests/data/demo_schema.txt \
        tests/data/demo_table.pdf

Each mapping file records which model produced it and when, under a ``metadata`` field:

.. code-block:: javascript

    {
      "tables": [ ... ],
      "citation": "...",
      "metadata": {
        "model": "google-gla:gemini-2.5-flash",
        "date": "2026-03-23T10:00:00+00:00"
      }
    }

Merging
=======

``paper2table`` also provides a table merging program called ``tablemerge``.
In order to be able to use it, you'll need to first generate some metadata. You can produce it using the
same ``paper2table`` command:

.. code-block:: bash

    # this command will create a new directory with the resultset, adding a metadata file
    # suitable for use with tablemerge command
    $ paper2table -t -o tests/data/tables tests/data/demo_table.pdf

To resume an interrupted run or add new papers to an existing resultset, use ``--append`` with the UUID of the resultset:

.. code-block:: bash

    # append new papers to an existing resultset
    # papers already present in the resultset are skipped automatically
    $ paper2table -t -o tests/data/tables --append <uuid> new_papers/*.pdf

``--append`` aborts if the reader or model of the current invocation does not match the one recorded in the existing resultset.

After doing this, you can merge tables like this:

.. code-block:: bash

    $ tablemerge -o tests/data/merges tests/data/demo_resultsets/*

Column alignment
----------------

When different ``paper2table`` runs produce numeric column names (``0``, ``1``, ``2``) instead of semantic ones, ``tablemerge`` can align them automatically.

``--jaccard-column-alignment`` uses Jaccard similarity on column values to detect which numeric column corresponds to which semantic column:

.. code-block:: bash

    $ tablemerge --jaccard-column-alignment tests/data/demo_resultsets/*

``--column-alignment-threshold`` sets the minimum similarity score (default: 0.5):

.. code-block:: bash

    $ tablemerge --jaccard-column-alignment --column-alignment-threshold 0.6 tests/data/demo_resultsets/*

``--semantic-column-alignment`` adds an NLP-based pass (spaCy) after Jaccard, comparing column values semantically against column names. Requires a spaCy model:

.. code-block:: bash

    $ python -m spacy download en_core_web_md
    $ tablemerge --jaccard-column-alignment --semantic-column-alignment tests/data/demo_resultsets/*

Use ``--semantic-language`` to select the spaCy model language (``en`` or ``es``, default ``en``):

.. code-block:: bash

    $ python -m spacy download es_core_news_md
    $ tablemerge --jaccard-column-alignment --semantic-column-alignment --semantic-language es tests/data/demo_resultsets/*

Column aliases
--------------

``--column-aliases`` and ``--column-aliases-path`` let you define explicit renames applied during merging. The format is ``alias:target`` (same as the schema format):

.. code-block:: bash

    $ tablemerge --column-aliases "familia:family especie:species" tests/data/demo_resultsets/*

    $ tablemerge --column-aliases-path aliases.txt tests/data/demo_resultsets/*

Both flags can be used together; the file takes precedence on conflicts.

Column name hints
-----------------

``--column-names-hints`` and ``--column-names-hints-path`` supply the expected column
names for runs that produced only numeric column names (``0``, ``1``, …). Hints use the
same format as the ``-c`` flag in ``paper2table`` (whitespace- or comma-separated, ``#`` comments allowed):

.. code-block:: bash

    $ tablemerge --column-names-hints "species family color" tests/data/demo_resultsets/*

    $ tablemerge --column-names-hints-path hints.txt tests/data/demo_resultsets/*

Both flags can be combined; their hint lists are merged.

``--hints-column-alignment`` activates hints-based column renaming: if at least one
non-empty value in the first non-empty row of a table with numeric column names matches
a hint, all numeric columns are renamed to their normalized first-row values (even
columns whose value is not in the hints list). This pass runs before all other alignment steps:

.. code-block:: bash

    $ tablemerge --column-names-hints "species family color" --hints-column-alignment tests/data/demo_resultsets/*

When ``--remove-header-rows`` is combined with hints, any row containing at least one
non-semantic cell value that matches a hint is also removed, in addition to the usual
semantic-column check:

.. code-block:: bash

    $ tablemerge --column-names-hints "species family color" --remove-header-rows tests/data/demo_resultsets/*

Schema
------

``-p`` accepts either a file path or an inline schema string:

.. code-block:: bash

    $ tablemerge -p "family:str species:str" --filter-schema-columns tests/data/demo_resultsets/*

    $ tablemerge -p tests/data/demo_schema.txt --filter-schema-columns tests/data/demo_resultsets/*

Compacting consecutive fragments
---------------------------------

When a table spans multiple pages, some readers split it into multiple separate tables.
``--compact-consecutive-fragments`` detects consecutive single-fragment tables and merges them
into one before the cross-run merge:

.. code-block:: bash

    # safe: only compact when both tables have semantic column names that match exactly
    $ tablemerge --compact-consecutive-fragments safe tests/data/demo_resultsets/*

    # unsafe: also compact when column count matches (for numeric column names)
    $ tablemerge --compact-consecutive-fragments unsafe tests/data/demo_resultsets/*


Generating stats
================

A tool ``tablestats`` is provided for getting some stats about the extracted tables. It can be used to query both the direct output of
a ``paper2table`` run or the results of a ``tablemerge`` output.

.. code-block:: bash

    # generate a json file with stats
    tablestats -o tests/data/stats.json tests/data/demo_resultsets/08ba0033-8b20-4dbb-bf4a-e2be1f194bc7/

    # pretty print stats to stdout
    # you can optionally sort results by number of extracted tables
    tablestats --sort desc tests/data/merges

    # if you only need to output empty files, use --empty
    # this is useful for debugging your results
    tablestats --empty tests/data/merges

Visualizing data
================

A tool ``table2html`` is provided for displaying a resultset:

.. code-block:: bash

    # it can be used both with the raw resultset of a paper2table run
    # or with the output of tablemerge
    table2html tests/data/merges


Running tests
=============

.. code-block:: bash

    $ tox

Running type checks
===================

.. code-block:: bash

    $ tox -e lint


``TablesFile`` format
=====================

``paper2table`` and ``tablemerge`` command output the the extracted tables data in a ``TablesFile`` file format,
(with extension ``.tables.json``). You can validate that those files follow the exact format using ``tablevalidate``:

.. code-block:: bash

    tablevalidate tests/data/demo_resultsets/*/*


The format is informally specified this way:

.. code-block:: javascript

    {
      "tables": [
        {
          "rows": [
            {
              "COLUMN_NAME_1": string | [{ "value": string, "agreement_level": integer }],
              "COLUMN_NAME_2": string | [{ "value": string, "agreement_level": integer }],
              "COLUMN_NAME_3": string | [{ "value": string, "agreement_level": integer }],
              "agreement_level_": integer // this is optional
            }
          ],
          "page": integer,
        },
        {
          "table_fragments": [
            {
              "rows": ..., // same schema as previous "rows" attribute
              "page": integer
            }
          ]
        }
      ],
      "citation": string | [{ "value": string, "agreement_level": integer }],
      "metadata": { // optional
        "filename": string,
      }
    }

You can also find a proper json schema definition in `tablesfile.schema.json <./tablesfile.schema.json>`_

Metadata files
==============

Both ``paper2table`` (with the ``-t`` flag) and ``tablemerge`` write a metadata file alongside the extracted tables.
The file has the same structure in both cases:

.. code-block:: javascript

    {
      "reader": string,   // e.g. "pdfplumber", "camelot", "agent", "hybrid-pdfplumber-gemini-2.5-flash", "tablemerge"
      "uuid": string,     // UUID identifying this run
      "datetime": string, // ISO 8601 timestamp of the run
      "sources": [        // only present in tablemerge output
        {
          "path": string,   // path to the source resultset directory
          "uuid": string,   // UUID of the source extraction run (if available)
          "reader": string  // reader used for the source run (if available)
        }
      ]
    }

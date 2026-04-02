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

Each mapping file records which model produced it and when, under a ``metadata`` field:

.. code-block:: javascript

    {
      "tables": [ ... ],
      "citation": "...",
      "metadata": {
        "model": "google-gla:gemini-2.5-flash",
        "date": "2026-03-23T10:00:00+00:00"
      }
    }pylint $(git ls-files 'src/**/*.py')

Merging
=======

``paper2table`` also provides a table merging program called ``tablemerge``.
In order to be able to use it, you'll need to first generate some metadata. You can produce it using the
same ``paper2table`` command:

.. code-block:: bash

    # this command will create a new directory with the resultset, adding a metadata file
    # suitable for use with tablemerge command
    $ paper2table -t -o tests/data/tables tests/data/demo_table.pdf

After doing this, you can merge tables like this:

.. code-block:: bash

    $ tablemerge -o tests/data/merges tests/data/demo_resultsets/*


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

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
* ``table2html``


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
    python -m filenorm -q PATH [PATH ...]

    # don't ask for confirmation. a log with each change will be printed
    python -m filenorm -y PATH [PATH ...]

Running
=======

``paper2table`` can read paper's table using three different backends:

  * the `pdfplumber <https://github.com/jsvine/pdfplumber>`_ package (this is the default option)
  * the `camelot <https://camelot-py.readthedocs.io/en/master/>`_ package (this is the default option)
  * an external generative agent. This  option is usually more robust, but slower, less deterministic and presents additional costs

.. code-block:: bash

    # basic usage
    $ python -m paper2table -p SCHEMA PATH [PATH ...]

    # e.g. use the default pdfplumber reader backend
    $ python -m paper2table -q tests/data/demo_table.pdf

    # e.g. use the pdfplumber reader specifying column name hints
    python -m paper2table -r pdfplumber -c tests/data/demo_column_hints.txt  tests/data/demo_table.pdf

    # e.g. use the camelot reader backend
    $ python -m paper2table -r camelot -q tests/data/demo_table.pdf

    # by default paper2table outputs data to stdout
    # but you can specify an output directory
    $ python -m paper2table -o .  tests/data/demo_table.pdf
    # result will be stored in demo_table.tables.json

    # e.g. use the agent backend with the Gemini API
    $ GEMINI_API_KEY=... python -m paper2table -r agent -m google-gla:gemini-2.5-flash -p tests/data/demo_schema.txt tests/data/demo_table.pdf

Merging
=======

``paper2table`` also provides a table merging program called ``tablemerge``. In order to be able to use it, you'll need to first generate some metadata. You can produce it using the
same ``paper2table`` command:

.. code-block:: bash

    # this command will create a new directory with the resultset, adding a metadata file
    # suitable for use with tablemerge command
    $ python -m paper2table -t -o tests/data/tables tests/data/demo_table.pdf

After doing this, you can merge tables like this:

.. code-block:: bash

    $ python -m tablemerge -o tests/data/merges tests/data/tables/*


Generating stats
================

A tool ``tablestats`` is provided for getting some stats about the extracted tables. It can be used to query both the direct output of
a ``paper2table`` run or the results of a ``tablemerge`` output.

.. code-block:: bash

    # generate a json file with stats
    python -m tablestats -o test/data/stats.json test/data/merges

    # pretty print stats to stdout
    # you can optionally sort results by number of extracted tables
    python -m tablestats --sort desc test/data/merges

    # if you only need to output empty files, use --empty
    # this is useful for debugging your results
    python -m tablestats --empty test/data/merges

Visualizing data
================

A tool ``table2html`` is provided for displaying a resultset:

.. code-block:: bash

    # it can be used both with the raw resultset of a paper2table run
    # or with the output of tablemerge
    python -m table2html ../test/data/merges


Running tests
=============

.. code-block:: bash

    $ tox


``TablesFile`` format
=====================

``paper2table`` and ``tablemerge`` command output the the extracted tables data in a ``TablesFile`` file format,
(with extension ``.tables.json``). You can validate that those files follow the exact format using ``tablevalidate``:

.. code-block:: bash

    python -m tablevalidate tests/data/tables/*


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
              "$agreement_level": interger // this is optional
            }
          ],
          "page": integer,
        },
        {
          "table_fragment": [
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

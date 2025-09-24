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


A longer description of your project goes here...


.. _pyscaffold-notes:

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

``paper2table`` can read paper's table using two different backends: using the `camelot <https://camelot-py.readthedocs.io/en/master/>`_ package (this is the default option) or an external
generate agent. This first one is usually faster and deterministic (and has no additional cost), but the latter is usually more robust.

.. code-block:: bash

    # basic usage
    $ python -m paper2table -p SCHEMA PATH [PATH ...]

    # e.g. use the default camelot reader backend
    $ python -m paper2table -q tests/data/demo_table.pdf

    # by default paper2table outputs data to stdout
    # but you can specify an output directory
    $ python -m paper2table -o .  tests/data/demo_table.pdf
    # result will be stored in demo_table.tables.json

    # e.g. use the agent backend with the Gemini API
    $ GEMINI_API_KEY=... python -m paper2table -r agent -m google-gla:gemini-2.5-flash -p tests/data/demo_schema.txt tests/data/demo_table.pdf


Running tests
=============

.. code-block:: bash

    $ tox
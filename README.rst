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

Running
=======

.. code-block:: bash

    python -m paper2table

    # e.g. pass Gemini API key
    GEMINI_API_KEY=.... python -m paper2table PATH


Running tests
=============

.. code-block:: bash

    $ tox
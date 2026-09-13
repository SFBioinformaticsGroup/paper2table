#!/bin/sh
set -e
case "$1" in
  filenorm|tablemerge|tablestats|table2html|table2csv|tablevalidate|tablegather)
    exec "$@"
    ;;
  *)
    exec paper2table "$@"
    ;;
esac

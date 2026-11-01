#!/usr/bin/env bash
# Finds a working Python 3 and runs sync.py with the given args.
# On Windows `python3` is often a Microsoft Store stub that exits with an error,
# so each candidate is test-run before use. Set SHOWRUNNER_PYTHON to skip the search.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for py in "$SHOWRUNNER_PYTHON" python3 python "py -3"; do
  [ -n "$py" ] || continue
  if $py -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    exec $py -X utf8 "$here/sync.py" "$@"
  fi
done
echo "showrunner: Python 3.8+ not found (set SHOWRUNNER_PYTHON)" >&2
exit 0

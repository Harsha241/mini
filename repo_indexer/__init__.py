"""
Compatibility initializer for the `repo_indexer` package.
Extends the package path to include the sibling `repo-indexer` directory
so imports like `repo_indexer.chunker.chunker` resolve correctly.
"""
import os
import sys

# Ensure subpackages can be found under the hyphenated folder name
_here = os.path.dirname(__file__)
_alt = os.path.normpath(os.path.join(_here, '..', 'repo-indexer'))
if os.path.isdir(_alt):
    if _alt not in sys.path:
        sys.path.append(_alt)
    try:
        __path__.append(_alt)  # type: ignore[name-defined]
    except Exception:
        pass


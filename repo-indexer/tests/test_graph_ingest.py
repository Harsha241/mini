import os
import pytest


def test_placeholder_ingest_config_exists():
    # Ensure CSV output dir path exists or at least the parent tools/joern exists
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'joern')
    assert os.path.isdir(base)




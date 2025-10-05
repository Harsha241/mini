from types import SimpleNamespace

from repo_indexer.graph.integration import retrieve_context_for_chunk


class FakeChroma:
    def search(self, query, n):
        return [
            {
                'id': 'c1',
                'document': 'def foo():\n  pass',
                'metadata': {'filepath': 'a.py', 'summary': 'foo', 'language': 'python', 'node_type': 'Function', 'start_line': 1, 'end_line': 2},
            }
        ]


class FakeSession:
    def run(self, query, **params):
        class R:
            def __iter__(self):
                return iter([
                    {'f': {'id': '1', 'name': 'foo', 'filepath': 'a.py', 'start_line': 1, 'end_line': 2},
                      'g': {'id': '2', 'name': 'bar', 'filepath': 'b.py', 'start_line': 10, 'end_line': 20},
                      'r': []}
                ])
        return R()


def test_retrieve_context_minimal():
    chunk = {'document': 'def foo():\n  pass', 'metadata': {'summary': 'foo function'}}
    ctx = retrieve_context_for_chunk(chunk, FakeChroma(), FakeSession(), n_semantic=1, hops=1)
    assert 'semantic_chunks' in ctx
    assert 'graph_text' in ctx
    assert len(ctx['semantic_chunks']) == 1
    assert 'CALL GRAPH' in ctx['graph_text']




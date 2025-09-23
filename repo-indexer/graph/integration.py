from __future__ import annotations

from typing import Any, Dict, List

from .query_graph import get_functions_for_chunk, get_call_subgraph, serialize_graph_for_model


def _format_semantic_result(item: Dict[str, Any]) -> Dict[str, Any]:
    meta = item.get('metadata', {})
    doc = item.get('document', '')
    snippet = doc[:800]
    return {
        'id': item.get('id'),
        'filepath': meta.get('filepath'),
        'summary': meta.get('summary'),
        'language': meta.get('language'),
        'node_type': meta.get('node_type'),
        'lines': [meta.get('start_line'), meta.get('end_line')],
        'snippet': snippet,
    }


def retrieve_context_for_chunk(
    chunk: Dict[str, Any],
    chroma_client,  # expects interface like CodeRetriever.collection.query
    neo4j_session,
    n_semantic: int = 5,
    hops: int = 3,
    max_graph_tokens: int = 800,
) -> Dict[str, Any]:
    # Semantic neighbors (reuse existing embedding if present, else search by summary/text)
    query_text = chunk.get('metadata', {}).get('summary') or chunk.get('document') or ''
    if hasattr(chroma_client, 'search'):
        results = chroma_client.search(query_text, n_semantic)
    else:
        # Assume `collection` style
        embedding = chroma_client.model.encode([query_text], convert_to_tensor=False)[0].tolist()
        results = chroma_client.collection.query(query_embeddings=[embedding], n_results=n_semantic)

    semantic_chunks = []
    if isinstance(results, list):
        semantic_chunks = [_format_semantic_result(r) for r in results]
    else:
        # format chroma raw response
        for i in range(len(results['ids'][0])):
            item = {
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
            }
            semantic_chunks.append(_format_semantic_result(item))

    # Graph context
    function_names = get_functions_for_chunk(chunk)
    nodes, edges = get_call_subgraph(neo4j_session, function_names, direction='both', hops=hops)
    graph_text = serialize_graph_for_model(nodes, edges, max_tokens=max_graph_tokens)

    return {
        'semantic_chunks': semantic_chunks,
        'graph_text': graph_text,
    }



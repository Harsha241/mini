#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any


SYMBOL_DEF_REGEX = re.compile(r"\b(def|function|func|public\s+\w+|private\s+\w+|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


@dataclass
class GraphNode:
    id: str
    label: str
    name: str
    filepath: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    signature: str | None = None


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str


def get_functions_for_chunk(chunk: Dict[str, Any]) -> List[str]:
    text = chunk.get('document') or chunk.get('text') or ''
    metadata = chunk.get('metadata') or {}
    candidates: List[str] = []

    # Prefer explicit metadata
    for key in ('function_name', 'name', 'symbol'):
        if metadata.get(key):
            candidates.append(str(metadata[key]))

    # Fallback: regex scan
    for m in SYMBOL_DEF_REGEX.finditer(text):
        candidates.append(m.group(2))

    # Deduplicate preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            unique.append(c)
            seen.add(c)
    return unique[:10]


def get_call_subgraph(session, function_names: List[str], direction: str = 'both', hops: int = 3) -> Tuple[List[GraphNode], List[GraphEdge]]:
    if not function_names:
        return [], []

    dir_pattern = {
        'out': '(:Function)-[r:CALLS*1..$hops]->(g:Function)',
        'in': '(g:Function)-[r:CALLS*1..$hops]->(:Function)',
        'both': '(:Function)-[r:CALLS*1..$hops]-(g:Function)'
    }.get(direction, '(:Function)-[r:CALLS*1..$hops]-(g:Function)')

    query = (
        "UNWIND $fnames AS fname "
        "MATCH (f:Function {name: fname})-" + dir_pattern + " "
        "RETURN DISTINCT f, g, r LIMIT 100"
    )

    result = session.run(query, fnames=function_names, hops=int(hops))

    nodes: Dict[str, GraphNode] = {}
    edges: List[GraphEdge] = []

    for record in result:
        f = record['f']
        g = record['g']
        rels = record['r']

        for node in (f, g):
            if node is None:
                continue
            nid = str(node.get('id', node.id))
            if nid not in nodes:
                nodes[nid] = GraphNode(
                    id=nid,
                    label='Function',
                    name=node.get('name'),
                    filepath=node.get('filepath'),
                    start_line=node.get('start_line'),
                    end_line=node.get('end_line'),
                    signature=node.get('signature'),
                )

        # Relationships path can be list
        if isinstance(rels, list):
            for r in rels:
                src = str(r.start_node.get('id', r.start_node.id))
                dst = str(r.end_node.get('id', r.end_node.id))
                edges.append(GraphEdge(source=src, target=dst, type='CALLS'))
        else:
            if rels is not None:
                src = str(rels.start_node.get('id', rels.start_node.id))
                dst = str(rels.end_node.get('id', rels.end_node.id))
                edges.append(GraphEdge(source=src, target=dst, type='CALLS'))

    return list(nodes.values()), edges


def _truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 3] + '...'


def serialize_graph_for_model(nodes: List[GraphNode], edges: List[GraphEdge], max_tokens: int = 800) -> str:
    # rough char budget ~ 4 chars/token
    max_chars = max(256, int(max_tokens * 4))
    id_to_node = {n.id: n for n in nodes}

    lines: List[str] = []
    lines.append("CALL GRAPH:")

    # List nodes with short info
    for idx, n in enumerate(nodes, 1):
        loc = f"{n.filepath}:{n.start_line}-{n.end_line}" if n.filepath else "?"
        sig = n.signature or ''
        lines.append(f"{idx}) {n.name} ({loc}) {sig}")

    # List edges
    lines.append("Edges (CALLS):")
    for e in edges[:200]:
        src = id_to_node.get(e.source)
        dst = id_to_node.get(e.target)
        if src and dst:
            lines.append(f"  {src.name} -> {dst.name}")

    text = "\n".join(lines)
    return _truncate(text, max_chars)



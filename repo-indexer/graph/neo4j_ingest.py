#!/usr/bin/env python3
"""
Ingest Joern-exported Neo4j CSVs into a running Neo4j instance and create indexes.

Usage:
  python -m repo_indexer.graph.neo4j_ingest --csv-dir tools/joern/out/neo4j_csvs --bolt bolt://localhost:7687 --user neo4j --password test-password

Notes:
  - Expects Neo4j 5.x with APOC plugin enabled (docker compose provided).
  - Uses Cypher LOAD CSV to import nodes and relationships.
  - Fails fast with clear error messages if CSVs or Neo4j are unavailable.
"""
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from neo4j import GraphDatabase
except Exception as exc:  # pragma: no cover
    raise SystemExit("neo4j driver not installed. Run: pip install neo4j") from exc


def _require_dir(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise SystemExit(f"CSV directory not found: {path}")


def _run_query(session, query: str, **params):
    return session.run(query, **params).consume()


def create_indexes(session) -> None:
    statements = [
        "CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name)",
        "CREATE INDEX function_id IF NOT EXISTS FOR (f:Function) ON (f.id)",
        "CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.path)",
        "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
    ]
    for stmt in statements:
        _run_query(session, stmt)


def load_csvs(session, csv_dir: Path) -> None:
    # Joern CSV layout can vary. We try common filenames and skip missing ones.
    # Files mounted under /imports inside neo4j container; for LOAD CSV we need file URL.
    base = csv_dir.resolve()
    def file_url(name: str) -> Optional[str]:
        p = base / name
        return f"file:///{name}" if p.exists() else None

    # Map common exports
    nodes_files = {
        'Function': file_url('nodes_Function.csv'),
        'File': file_url('nodes_File.csv'),
        'Class': file_url('nodes_TypeDecl.csv') or file_url('nodes_Class.csv'),
    }
    rels_files = {
        'CALLS': file_url('relationships_CALL.csv') or file_url('relationships_CALLS.csv'),
        'CONTAINS': file_url('relationships_CONTAINS.csv'),
    }

    # Load nodes
    if nodes_files['Function']:
        _run_query(session, (
            "LOAD CSV WITH HEADERS FROM $url AS row "
            "MERGE (f:Function {id: row.id}) "
            "SET f.name = coalesce(row.name, f.name), "
            "    f.signature = coalesce(row.signature, f.signature), "
            "    f.filepath = coalesce(row.filename, f.filepath), "
            "    f.start_line = toInteger(coalesce(row.lineNumberStart, row.startLine, 0)), "
            "    f.end_line = toInteger(coalesce(row.lineNumberEnd, row.endLine, 0))"
        ), url=nodes_files['Function'])

    if nodes_files['File']:
        _run_query(session, (
            "LOAD CSV WITH HEADERS FROM $url AS row "
            "MERGE (f:File {path: row.path})"
        ), url=nodes_files['File'])

    if nodes_files['Class']:
        _run_query(session, (
            "LOAD CSV WITH HEADERS FROM $url AS row "
            "MERGE (c:Class {id: row.id}) SET c.name = row.name"
        ), url=nodes_files['Class'])

    # Relationships
    if rels_files['CALLS']:
        _run_query(session, (
            "LOAD CSV WITH HEADERS FROM $url AS row "
            "MATCH (src:Function {id: row.startId}), (dst:Function {id: row.endId}) "
            "MERGE (src)-[r:CALLS]->(dst) "
            "SET r.type = coalesce(row.type, 'CALL')"
        ), url=rels_files['CALLS'])

    if rels_files['CONTAINS']:
        _run_query(session, (
            "LOAD CSV WITH HEADERS FROM $url AS row "
            "MATCH (a {id: row.startId}), (b {id: row.endId}) "
            "MERGE (a)-[:CONTAINS]->(b)"
        ), url=rels_files['CONTAINS'])


def main():
    parser = argparse.ArgumentParser(description="Ingest Joern Neo4j CSVs into Neo4j")
    parser.add_argument("--csv-dir", required=True, help="Path to Joern neo4j CSV output")
    parser.add_argument("--bolt", default="bolt://localhost:7687", help="Neo4j bolt URI")
    parser.add_argument("--user", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "test-password"), help="Neo4j password")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    _require_dir(csv_dir)

    driver = GraphDatabase.driver(args.bolt, auth=(args.user, args.password))
    try:
        with driver.session() as session:
            create_indexes(session)
            load_csvs(session, csv_dir)
    finally:
        driver.close()

    print("Ingestion complete.")


if __name__ == "__main__":
    main()



# Repository Indexer

A comprehensive codebase indexing and RAG (Retrieval-Augmented Generation) pipeline that uses Tree-sitter for AST-aware chunking and ChromaDB for vector storage.

## Features

- **AST-aware chunking** using Tree-sitter parsers for Python, JavaScript, and Java
- **Semantic chunking** based on code structure (functions, classes, methods, etc.)
- **Vector embeddings** using SentenceTransformers
- **Persistent storage** with ChromaDB
- **Intelligent overlap** between adjacent chunks for context preservation
- **Fallback chunking** when Tree-sitter parsing fails
- **Comprehensive testing** and pilot validation

## Installation

### Prerequisites

```bash
# Install Python dependencies
pip install tree-sitter sentence-transformers chromadb tiktoken

# Install tree-sitter language bindings (optional, for better parsing)
pip install tree-sitter-python tree-sitter-javascript tree-sitter-java
```

### Environment Variables

```bash
# Optional: Custom model for embeddings
export SENTENCE_MODEL="all-mpnet-base-v2"

# Optional: Custom ChromaDB path
export CHROMA_PATH="./repo-indexer/chroma_store"

# Optional: Precompiled tree-sitter library
export TS_LANG_SO="/path/to/tree-sitter-languages.so"
```

## Usage

### 1. Chunk Repository Files

```bash
# Basic chunking
python repo-indexer/chunker/chunker.py --root . --out repo-indexer/outputs

# With custom parameters
python repo-indexer/chunker/chunker.py \
    --root /path/to/repo \
    --out repo-indexer/outputs \
    --max-tokens 25000 \
    --min-tokens 50 \
    --overlap 1000

# Dry run to see what would be processed
python repo-indexer/chunker/chunker.py --root . --dry-run
```

### 2. Generate Embeddings

```bash
# Generate embeddings and store in ChromaDB
python repo-indexer/embeddings/embed_chroma.py \
    --chunks repo-indexer/outputs/chunks.jsonl \
    --chroma-path ./repo-indexer/chroma_store \
    --batch-size 64

# Force re-embedding of existing chunks
python repo-indexer/embeddings/embed_chroma.py --force
```

### 3. Query Code

```bash
# Search for code
python repo-indexer/retrieval/query.py \
    --query "how is authentication implemented?" \
    --n 5

# Search in specific language
python repo-indexer/retrieval/query.py \
    --query "database connection" \
    --language python \
    --n 3

# Search in specific file
python repo-indexer/retrieval/query.py \
    --query "error handling" \
    --filepath "src/utils/helpers.py" \
    --n 5
```

### 4. Run Pilot Test

```bash
# Run complete pilot test
python repo-indexer/run_pilot.py

# With custom parameters
python repo-indexer/run_pilot.py \
    --chunks repo-indexer/outputs/chunks.jsonl \
    --chroma-path ./repo-indexer/chroma_store \
    --query "how is data validation handled?"
```

## Output Files

### Chunks (chunks.jsonl)
Each line contains a JSON object with:
```json
{
  "id": "sha1:filepath:start:end",
  "filepath": "src/utils/helpers.py",
  "language": "python",
  "node_type": "function",
  "start_line": 10,
  "end_line": 25,
  "text": "def validate_input(data):\n    ...",
  "summary": "Function: def validate_input(data):...",
  "tokens_estimate": 150,
  "parents": [],
  "imports": ["import json", "from typing import Dict"],
  "examples": [],
  "code_fingerprint": "abc123...",
  "last_modified": "2024-01-01T12:00:00"
}
```

### Manifest (manifest.json)
```json
{
  "scanned_folders": 15,
  "total_files": 42,
  "parsed_files": 40,
  "failed_files": 2,
  "total_chunks": 156,
  "avg_chunk_tokens": 1200,
  "chunks_by_language": {
    "python": 89,
    "javascript": 45,
    "java": 22
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

### Error Logs
- `parse_errors.log`: Tree-sitter parsing errors
- `pipeline_errors.log`: Embedding and ChromaDB errors

## Configuration

### Chunking Rules

- **Max tokens per chunk**: 25,000 (configurable)
- **Min tokens per chunk**: 50 (configurable)
- **Overlap between chunks**: 500-1,500 tokens (configurable)
- **Node boundaries**: Functions, methods, classes, modules, test cases
- **Fallback**: Line-based chunking when AST parsing fails

### Supported Languages

- **Python** (.py)
- **JavaScript** (.js, .jsx)
- **TypeScript** (.ts, .tsx)
- **Java** (.java)

### Tree-sitter Queries

Query files are located in `repo-indexer/chunker/queries/`:
- `python.scm`: Python AST patterns
- `javascript.scm`: JavaScript/TypeScript AST patterns
- `java.scm`: Java AST patterns

## Testing

```bash
# Run unit tests
python -m pytest repo-indexer/tests/test_chunking.py -v

# Run specific test
python -m pytest repo-indexer/tests/test_chunking.py::TestTokenEstimator::test_estimate_tokens_basic -v
```

## Architecture

```
repo-indexer/
├── chunker/
│   ├── chunker.py          # Main chunking logic
│   └── queries/            # Tree-sitter query files
│       ├── python.scm
│       ├── javascript.scm
│       └── java.scm
├── embeddings/
│   └── embed_chroma.py     # ChromaDB embedding storage
├── retrieval/
│   └── query.py            # Query interface
├── tests/
│   └── test_chunking.py    # Unit tests
├── outputs/                # Generated files
│   ├── chunks.jsonl
│   ├── manifest.json
│   ├── parse_errors.log
│   └── pilot_results.json
└── run_pilot.py            # Pilot test script
```

## Troubleshooting

### Common Issues

1. **Tree-sitter not found**
   ```bash
   pip install tree-sitter
   ```

2. **Language bindings missing**
   ```bash
   pip install tree-sitter-python tree-sitter-javascript tree-sitter-java
   ```

3. **ChromaDB connection failed**
   - Check if ChromaDB is installed: `pip install chromadb`
   - Ensure write permissions to the storage directory

4. **Memory issues with large files**
   - Reduce batch size: `--batch-size 32`
   - Increase max tokens per chunk: `--max-tokens 50000`

### Performance Tips

- Use SSD storage for ChromaDB for better performance
- Adjust batch sizes based on available memory
- Consider using smaller embedding models for faster processing
- Use `--dry-run` to estimate processing time

## Contributing

1. Add new language support by creating query files in `queries/`
2. Extend the chunker to support additional node types
3. Improve the fallback chunking algorithm
4. Add more comprehensive tests

## License

This project is part of a codebase indexing system. Please refer to the main project license.


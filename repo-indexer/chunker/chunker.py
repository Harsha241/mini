#!/usr/bin/env python3
"""
AST-aware code chunker using Tree-sitter for Python, JavaScript, and Java.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import tree_sitter
    from tree_sitter import Language, Parser
except ImportError:
    tree_sitter = None
    Language = None
    Parser = None

try:
    import tiktoken
except ImportError:
    tiktoken = None

# Add the existing file traversal module to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src" / "inputandfilehandling"))
from filetraversal import traverse_file_system, TraverseFileSystemParams, ProcessFileParams


class TokenEstimator:
    """Token estimation using tiktoken or fallback method."""
    
    def __init__(self):
        self.encoder = None
        if tiktoken:
            try:
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Conservative fallback: ~4 chars per token
            return len(text) // 4


class TreeSitterChunker:
    """Tree-sitter based AST chunker."""
    
    def __init__(self, queries_dir: Path, max_tokens: int = 25000, min_tokens: int = 50, overlap_tokens: int = 1000):
        self.queries_dir = queries_dir
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.token_estimator = TokenEstimator()
        self.parsers = {}
        self.queries = {}
        self.parse_errors = []
        
        self._setup_parsers()
        self._load_queries()
    
    def _setup_parsers(self):
        """Setup Tree-sitter parsers for supported languages."""
        if not tree_sitter:
            logging.warning("Tree-sitter not available, falling back to line-based chunking")
            return
        
        # Language mappings
        languages = {
            'python': 'python',
            'javascript': 'javascript', 
            'typescript': 'typescript',
            'java': 'java'
        }
        
        for lang_name, ts_lang in languages.items():
            try:
                # Try to load language from environment or use built-in
                if os.getenv('TS_LANG_SO'):
                    lang_path = os.getenv('TS_LANG_SO')
                    language = Language(lang_path, ts_lang)
                else:
                    # This would need tree-sitter language bindings installed
                    # For now, we'll handle the ImportError gracefully
                    continue
                
                parser = Parser()
                parser.set_language(language)
                self.parsers[lang_name] = parser
                logging.info(f"Loaded Tree-sitter parser for {lang_name}")
            except Exception as e:
                logging.warning(f"Could not load Tree-sitter parser for {lang_name}: {e}")
                self.parse_errors.append(f"Parser setup failed for {lang_name}: {e}")
    
    def _load_queries(self):
        """Load Tree-sitter queries from files."""
        query_files = {
            'python': 'python.scm',
            'javascript': 'javascript.scm',
            'java': 'java.scm'
        }
        
        for lang, filename in query_files.items():
            query_path = self.queries_dir / filename
            if query_path.exists():
                try:
                    with open(query_path, 'r', encoding='utf-8') as f:
                        query_text = f.read()
                    self.queries[lang] = query_text
                    logging.info(f"Loaded query for {lang}")
                except Exception as e:
                    logging.warning(f"Could not load query for {lang}: {e}")
                    self.parse_errors.append(f"Query loading failed for {lang}: {e}")
    
    def _get_language(self, filepath: str) -> str:
        """Determine language from file extension."""
        ext = Path(filepath).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java'
        }
        return lang_map.get(ext, 'unknown')
    
    def _parse_with_tree_sitter(self, content: str, language: str) -> Optional[Any]:
        """Parse content using Tree-sitter."""
        if language not in self.parsers or language not in self.queries:
            return None
        
        try:
            parser = self.parsers[language]
            tree = parser.parse(bytes(content, 'utf8'))
            return tree
        except Exception as e:
            self.parse_errors.append(f"Tree-sitter parsing failed for {language}: {e}")
            return None
    
    def _extract_nodes_with_query(self, tree: Any, language: str) -> List[Dict]:
        """Extract relevant nodes using Tree-sitter query."""
        if language not in self.queries:
            return []
        
        try:
            query = tree.query(self.queries[language])
            captures = query.captures(tree.root_node)
            
            nodes = []
            for node, capture_name in captures:
                if node.type in ['comment', 'line_comment', 'block_comment']:
                    continue
                
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                nodes.append({
                    'type': node.type,
                    'name': self._extract_node_name(node, capture_name),
                    'start_line': start_line,
                    'end_line': end_line,
                    'text': node.text.decode('utf8') if hasattr(node, 'text') else '',
                    'capture_name': capture_name
                })
            
            return nodes
        except Exception as e:
            self.parse_errors.append(f"Query execution failed for {language}: {e}")
            return []
    
    def _extract_node_name(self, node: Any, capture_name: str) -> str:
        """Extract meaningful name from AST node."""
        # This is a simplified implementation
        # In practice, you'd traverse the node to find identifier children
        return capture_name or node.type
    
    def _fallback_chunking(self, content: str, filepath: str) -> List[Dict]:
        """Fallback to line-based chunking when Tree-sitter fails."""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for i, line in enumerate(lines, 1):
            line_tokens = self.token_estimator.estimate_tokens(line)
            
            if current_tokens + line_tokens > self.max_tokens and current_chunk:
                # Save current chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'type': 'block',
                    'name': f'block_{len(chunks) + 1}',
                    'start_line': i - len(current_chunk),
                    'end_line': i - 1,
                    'text': chunk_text,
                    'capture_name': 'fallback',
                    'parser_fallback': True
                })
                current_chunk = [line]
                current_tokens = line_tokens
            else:
                current_chunk.append(line)
                current_tokens += line_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                'type': 'block',
                'name': f'block_{len(chunks) + 1}',
                'start_line': len(lines) - len(current_chunk) + 1,
                'end_line': len(lines),
                'text': chunk_text,
                'capture_name': 'fallback',
                'parser_fallback': True
            })
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Merge chunks that are too small."""
        if not chunks:
            return chunks
        
        merged = []
        i = 0
        
        while i < len(chunks):
            current = chunks[i]
            current_tokens = self.token_estimator.estimate_tokens(current['text'])
            
            if current_tokens < self.min_tokens and i < len(chunks) - 1:
                # Try to merge with next chunk
                next_chunk = chunks[i + 1]
                next_tokens = self.token_estimator.estimate_tokens(next_chunk['text'])
                
                if current_tokens + next_tokens <= self.max_tokens:
                    # Merge chunks
                    merged_text = current['text'] + '\n' + next_chunk['text']
                    merged.append({
                        'type': 'merged',
                        'name': f"{current['name']}_merged_{next_chunk['name']}",
                        'start_line': current['start_line'],
                        'end_line': next_chunk['end_line'],
                        'text': merged_text,
                        'capture_name': 'merged',
                        'parser_fallback': current.get('parser_fallback', False) or next_chunk.get('parser_fallback', False)
                    })
                    i += 2
                    continue
            
            merged.append(current)
            i += 1
        
        return merged
    
    def _add_overlap(self, chunks: List[Dict], content: str) -> List[Dict]:
        """Add overlap between adjacent chunks."""
        if len(chunks) <= 1:
            return chunks
        
        lines = content.split('\n')
        overlapped = []
        
        for i, chunk in enumerate(chunks):
            start_line = chunk['start_line'] - 1  # Convert to 0-based
            end_line = chunk['end_line']  # Already 1-based, convert to 0-based for slicing
            
            # Add overlap from previous chunk
            if i > 0:
                prev_chunk = chunks[i - 1]
                prev_end = prev_chunk['end_line']  # 1-based
                overlap_start = max(0, prev_end - self.overlap_tokens // 4)  # Rough line estimate
                overlap_lines = lines[overlap_start:prev_end]
                overlap_text = '\n'.join(overlap_lines)
                chunk['text'] = overlap_text + '\n' + chunk['text']
                chunk['start_line'] = overlap_start + 1
            
            # Add overlap to next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                next_start = next_chunk['start_line'] - 1  # Convert to 0-based
                overlap_end = min(len(lines), next_start + self.overlap_tokens // 4)
                overlap_lines = lines[next_start:overlap_end]
                overlap_text = '\n'.join(overlap_lines)
                chunk['text'] = chunk['text'] + '\n' + overlap_text
                chunk['end_line'] = overlap_end
            
            overlapped.append(chunk)
        
        return overlapped
    
    def chunk_file(self, filepath: str, content: str) -> List[Dict]:
        """Chunk a single file."""
        language = self._get_language(filepath)
        
        # Try Tree-sitter parsing first
        tree = self._parse_with_tree_sitter(content, language)
        if tree:
            nodes = self._extract_nodes_with_query(tree, language)
        else:
            nodes = []
        
        # Fallback to line-based chunking if no nodes found
        if not nodes:
            nodes = self._fallback_chunking(content, filepath)
        
        # Merge small chunks
        nodes = self._merge_small_chunks(nodes)
        
        # Add overlap
        nodes = self._add_overlap(nodes, content)
        
        return nodes
    
    def create_chunk_id(self, filepath: str, start_line: int, end_line: int, text: str) -> str:
        """Create unique chunk ID."""
        content = f"{filepath}:{start_line}:{end_line}:{text}"
        return f"sha1:{hashlib.sha1(content.encode()).hexdigest()}"
    
    def create_code_fingerprint(self, filepath: str, start_line: int, end_line: int, text: str) -> str:
        """Create code fingerprint for change detection."""
        content = f"{filepath}:{start_line}:{end_line}:{text}"
        return hashlib.sha1(content.encode()).hexdigest()
    
    def generate_summary(self, text: str, node_type: str) -> str:
        """Generate a simple summary for the chunk."""
        lines = text.strip().split('\n')
        first_line = lines[0].strip() if lines else ""
        
        if node_type in ['function', 'method']:
            return f"Function: {first_line[:100]}..."
        elif node_type in ['class']:
            return f"Class: {first_line[:100]}..."
        elif node_type in ['import', 'import_statement']:
            return f"Import: {first_line}"
        else:
            return f"{node_type.title()}: {first_line[:100]}..."
    
    def extract_imports(self, text: str, language: str) -> List[str]:
        """Extract import statements from text."""
        imports = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if language == 'python':
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
            elif language in ['javascript', 'typescript']:
                if line.startswith('import ') or line.startswith('require('):
                    imports.append(line)
            elif language == 'java':
                if line.startswith('import '):
                    imports.append(line)
        
        return imports


class RepoChunker:
    """Main repository chunker."""
    
    def __init__(self, root_path: str, output_dir: str, **kwargs):
        self.root_path = Path(root_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize chunker
        queries_dir = Path(__file__).parent / "queries"
        self.chunker = TreeSitterChunker(queries_dir, **kwargs)
        
        # Statistics
        self.stats = {
            'scanned_folders': 0,
            'total_files': 0,
            'parsed_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'chunks_by_language': {},
            'avg_chunk_tokens': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = self.output_dir / "parse_errors.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def process_file(self, file_params: ProcessFileParams):
        """Process a single file."""
        filepath = file_params.file_path
        relative_path = Path(filepath).relative_to(self.root_path)
        
        self.stats['total_files'] += 1
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Get file modification time
            mtime = Path(filepath).stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime).isoformat()
            
            # Chunk the file
            chunks = self.chunker.chunk_file(filepath, content)
            
            if chunks:
                self.stats['parsed_files'] += 1
                language = self.chunker._get_language(filepath)
                
                if language not in self.stats['chunks_by_language']:
                    self.stats['chunks_by_language'][language] = 0
                self.stats['chunks_by_language'][language] += len(chunks)
                
                # Write chunks to output
                self._write_chunks(relative_path, chunks, language, last_modified)
            else:
                self.stats['failed_files'] += 1
                logging.warning(f"No chunks generated for {filepath}")
                
        except Exception as e:
            self.stats['failed_files'] += 1
            logging.error(f"Error processing {filepath}: {e}")
    
    def process_folder(self, folder_params):
        """Process a folder (increment counter)."""
        self.stats['scanned_folders'] += 1
    
    def _write_chunks(self, filepath: Path, chunks: List[Dict], language: str, last_modified: str):
        """Write chunks to JSONL file."""
        output_file = self.output_dir / "chunks.jsonl"
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for chunk in chunks:
                chunk_id = self.chunker.create_chunk_id(
                    str(filepath), chunk['start_line'], chunk['end_line'], chunk['text']
                )
                
                tokens_estimate = self.chunker.token_estimator.estimate_tokens(chunk['text'])
                self.stats['total_chunks'] += 1
                
                chunk_data = {
                    "id": chunk_id,
                    "filepath": str(filepath),
                    "language": language,
                    "node_type": chunk['type'],
                    "start_line": chunk['start_line'],
                    "end_line": chunk['end_line'],
                    "text": chunk['text'],
                    "summary": self.chunker.generate_summary(chunk['text'], chunk['type']),
                    "tokens_estimate": tokens_estimate,
                    "parents": [],  # Could be enhanced to track parent relationships
                    "imports": self.chunker.extract_imports(chunk['text'], language),
                    "examples": [],  # Could be enhanced to extract usage examples
                    "code_fingerprint": self.chunker.create_code_fingerprint(
                        str(filepath), chunk['start_line'], chunk['end_line'], chunk['text']
                    ),
                    "last_modified": last_modified
                }
                
                # Add parser fallback flag if applicable
                if chunk.get('parser_fallback'):
                    chunk_data['parser_fallback'] = True
                
                f.write(json.dumps(chunk_data) + '\n')
    
    def write_manifest(self):
        """Write manifest file."""
        # Calculate average chunk tokens
        if self.stats['total_chunks'] > 0:
            total_tokens = sum(
                self.stats['chunks_by_language'].get(lang, 0) * 1000  # Rough estimate
                for lang in self.stats['chunks_by_language']
            )
            self.stats['avg_chunk_tokens'] = total_tokens // self.stats['total_chunks']
        
        manifest_file = self.output_dir / "manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)
    
    def run(self, dry_run: bool = False):
        """Run the chunking process."""
        logging.info(f"Starting chunking process for {self.root_path}")
        
        if dry_run:
            logging.info("DRY RUN MODE - No files will be processed")
            return
        
        # Clear output files
        chunks_file = self.output_dir / "chunks.jsonl"
        if chunks_file.exists():
            chunks_file.unlink()
        
        # Configure traversal
        params = TraverseFileSystemParams(
            input_path=str(self.root_path),
            process_file=self.process_file,
            process_folder=self.process_folder,
            ignore=[
                '__pycache__', '*.pyc', '.venv', 'env', '.env',
                '.git', '.gitignore', '.gitattributes',
                'node_modules', 'package-lock.json', 'yarn.lock',
                '.idea', '.vscode', '*.sublime-*',
                '.DS_Store', 'Thumbs.db',
                '*.log', '*.tmp', '*.swp',
                'Dockerfile', '*.dockerfile', '.dockerignore',
                '*.env', '.env.example', 'venv', '*.egg-info'
            ]
        )
        
        # Run traversal
        traverse_file_system(params)
        
        # Write manifest
        self.write_manifest()
        
        # Write parse errors
        if self.chunker.parse_errors:
            error_file = self.output_dir / "parse_errors.log"
            with open(error_file, 'a', encoding='utf-8') as f:
                for error in self.chunker.parse_errors:
                    f.write(f"{datetime.now().isoformat()} - {error}\n")
        
        logging.info(f"Chunking complete. Processed {self.stats['total_files']} files, "
                    f"generated {self.stats['total_chunks']} chunks")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="AST-aware code chunker")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--out", default="repo-indexer/outputs", help="Output directory")
    parser.add_argument("--max-tokens", type=int, default=25000, help="Maximum tokens per chunk")
    parser.add_argument("--min-tokens", type=int, default=50, help="Minimum tokens per chunk")
    parser.add_argument("--overlap", type=int, default=1000, help="Overlap tokens between chunks")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    chunker = RepoChunker(
        root_path=args.root,
        output_dir=args.out,
        max_tokens=args.max_tokens,
        min_tokens=args.min_tokens,
        overlap_tokens=args.overlap
    )
    
    chunker.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()


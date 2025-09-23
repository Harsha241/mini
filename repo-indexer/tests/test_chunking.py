#!/usr/bin/env python3
"""
Unit tests for the chunking functionality.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from chunker.chunker import TreeSitterChunker, RepoChunker, TokenEstimator


class TestTokenEstimator(unittest.TestCase):
    """Test token estimation functionality."""
    
    def setUp(self):
        self.estimator = TokenEstimator()
    
    def test_estimate_tokens_basic(self):
        """Test basic token estimation."""
        text = "Hello world, this is a test."
        tokens = self.estimator.estimate_tokens(text)
        self.assertGreater(tokens, 0)
        self.assertIsInstance(tokens, int)
    
    def test_estimate_tokens_empty(self):
        """Test token estimation with empty text."""
        tokens = self.estimator.estimate_tokens("")
        self.assertEqual(tokens, 0)
    
    def test_estimate_tokens_long_text(self):
        """Test token estimation with longer text."""
        text = "This is a longer text that should have more tokens. " * 100
        tokens = self.estimator.estimate_tokens(text)
        self.assertGreater(tokens, 10)


class TestTreeSitterChunker(unittest.TestCase):
    """Test Tree-sitter chunker functionality."""
    
    def setUp(self):
        queries_dir = Path(__file__).parent.parent / "chunker" / "queries"
        self.chunker = TreeSitterChunker(queries_dir, max_tokens=1000, min_tokens=10, overlap_tokens=100)
    
    def test_get_language_python(self):
        """Test language detection for Python files."""
        language = self.chunker._get_language("test.py")
        self.assertEqual(language, "python")
    
    def test_get_language_javascript(self):
        """Test language detection for JavaScript files."""
        language = self.chunker._get_language("test.js")
        self.assertEqual(language, "javascript")
    
    def test_get_language_java(self):
        """Test language detection for Java files."""
        language = self.chunker._get_language("Test.java")
        self.assertEqual(language, "java")
    
    def test_get_language_unknown(self):
        """Test language detection for unknown files."""
        language = self.chunker._get_language("test.txt")
        self.assertEqual(language, "unknown")
    
    def test_create_chunk_id(self):
        """Test chunk ID creation."""
        chunk_id = self.chunker.create_chunk_id("test.py", 1, 10, "print('hello')")
        self.assertTrue(chunk_id.startswith("sha1:"))
        self.assertEqual(len(chunk_id), 45)  # "sha1:" + 40 char hash
    
    def test_create_code_fingerprint(self):
        """Test code fingerprint creation."""
        fingerprint = self.chunker.create_code_fingerprint("test.py", 1, 10, "print('hello')")
        self.assertEqual(len(fingerprint), 40)  # SHA1 hex length
        self.assertIsInstance(fingerprint, str)
    
    def test_generate_summary_function(self):
        """Test summary generation for functions."""
        text = "def hello_world():\n    print('Hello, World!')"
        summary = self.chunker.generate_summary(text, "function")
        self.assertIn("Function:", summary)
        self.assertIn("def hello_world", summary)
    
    def test_generate_summary_class(self):
        """Test summary generation for classes."""
        text = "class MyClass:\n    def __init__(self):\n        pass"
        summary = self.chunker.generate_summary(text, "class")
        self.assertIn("Class:", summary)
        self.assertIn("class MyClass", summary)
    
    def test_extract_imports_python(self):
        """Test import extraction for Python."""
        text = "import os\nfrom pathlib import Path\nprint('hello')"
        imports = self.chunker.extract_imports(text, "python")
        self.assertIn("import os", imports)
        self.assertIn("from pathlib import Path", imports)
        self.assertNotIn("print('hello')", imports)
    
    def test_extract_imports_javascript(self):
        """Test import extraction for JavaScript."""
        text = "import React from 'react'\nconst x = 1\nrequire('fs')"
        imports = self.chunker.extract_imports(text, "javascript")
        self.assertIn("import React from 'react'", imports)
        self.assertIn("require('fs')", imports)
        self.assertNotIn("const x = 1", imports)
    
    def test_extract_imports_java(self):
        """Test import extraction for Java."""
        text = "import java.util.List;\npublic class Test {\n    // code\n}"
        imports = self.chunker.extract_imports(text, "java")
        self.assertIn("import java.util.List;", imports)
        self.assertNotIn("public class Test", imports)
    
    def test_fallback_chunking(self):
        """Test fallback chunking when Tree-sitter fails."""
        content = "line1\nline2\nline3\nline4\nline5"
        chunks = self.chunker._fallback_chunking(content, "test.py")
        
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIn('text', chunk)
            self.assertIn('start_line', chunk)
            self.assertIn('end_line', chunk)
            self.assertTrue(chunk['parser_fallback'])
    
    def test_merge_small_chunks(self):
        """Test merging of small chunks."""
        chunks = [
            {'text': 'short', 'start_line': 1, 'end_line': 1, 'type': 'block'},
            {'text': 'also short', 'start_line': 2, 'end_line': 2, 'type': 'block'},
            {'text': 'this is a much longer chunk that should not be merged', 'start_line': 3, 'end_line': 3, 'type': 'block'}
        ]
        
        # Mock token estimation to make first two chunks small
        with patch.object(self.chunker.token_estimator, 'estimate_tokens', side_effect=lambda x: 5 if len(x) < 20 else 100):
            merged = self.chunker._merge_small_chunks(chunks)
            
            # Should have 2 chunks (first two merged, third unchanged)
            self.assertEqual(len(merged), 2)
            self.assertIn('merged', merged[0]['name'])


class TestRepoChunker(unittest.TestCase):
    """Test repository chunker functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir()
        
        # Create a simple test file
        self.test_file = Path(self.temp_dir) / "test.py"
        with open(self.test_file, 'w') as f:
            f.write("def hello():\n    print('Hello, World!')\n\nclass Test:\n    pass\n")
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_repo_chunker_initialization(self):
        """Test repository chunker initialization."""
        chunker = RepoChunker(
            root_path=self.temp_dir,
            output_dir=str(self.output_dir)
        )
        
        self.assertEqual(chunker.root_path, Path(self.temp_dir))
        self.assertEqual(chunker.output_dir, self.output_dir)
        self.assertIsInstance(chunker.stats, dict)
    
    def test_process_file(self):
        """Test file processing."""
        chunker = RepoChunker(
            root_path=self.temp_dir,
            output_dir=str(self.output_dir)
        )
        
        # Mock the chunker to avoid Tree-sitter dependencies
        with patch.object(chunker.chunker, 'chunk_file', return_value=[
            {'type': 'function', 'name': 'hello', 'start_line': 1, 'end_line': 2, 'text': "def hello():\n    print('Hello, World!')", 'capture_name': 'function'}
        ]):
            file_params = Mock()
            file_params.file_path = str(self.test_file)
            
            chunker.process_file(file_params)
            
            # Check that chunks file was created
            chunks_file = self.output_dir / "chunks.jsonl"
            self.assertTrue(chunks_file.exists())
            
            # Check chunk content
            with open(chunks_file, 'r') as f:
                chunk_data = json.loads(f.readline())
                self.assertIn('id', chunk_data)
                self.assertIn('filepath', chunk_data)
                self.assertIn('text', chunk_data)
    
    def test_write_manifest(self):
        """Test manifest writing."""
        chunker = RepoChunker(
            root_path=self.temp_dir,
            output_dir=str(self.output_dir)
        )
        
        # Set some stats
        chunker.stats['total_files'] = 5
        chunker.stats['total_chunks'] = 10
        
        chunker.write_manifest()
        
        manifest_file = self.output_dir / "manifest.json"
        self.assertTrue(manifest_file.exists())
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
            self.assertEqual(manifest['total_files'], 5)
            self.assertEqual(manifest['total_chunks'], 10)


if __name__ == '__main__':
    unittest.main()


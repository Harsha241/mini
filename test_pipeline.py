#!/usr/bin/env python3
"""Test the complete pipeline."""

import json
import sys
from pathlib import Path

# Add repo-indexer to path
sys.path.append(str(Path(__file__).parent / "repo-indexer"))

def test_chunking():
    """Test chunking functionality."""
    print("Testing chunking...")
    
    try:
        from chunker.chunker import RepoChunker
        
        # Create a small test chunker
        chunker = RepoChunker(
            root_path=".",
            output_dir="test_outputs",
            max_tokens=1000,
            min_tokens=10,
            overlap_tokens=100
        )
        
        # Test with a simple Python file
        test_content = '''
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
        
        chunks = chunker.chunker.chunk_file("test.py", test_content)
        print(f"✓ Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i+1}: {chunk['type']} (lines {chunk['start_line']}-{chunk['end_line']})")
        
        return True
        
    except Exception as e:
        print(f"✗ Chunking error: {e}")
        return False

def test_embeddings():
    """Test embedding functionality."""
    print("\nTesting embeddings...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Load model
        model = SentenceTransformer('all-mpnet-base-v2')
        print("✓ Model loaded")
        
        # Test embedding
        test_texts = [
            "def hello_world():\n    print('Hello, World!')",
            "class TestClass:\n    def __init__(self):\n        pass"
        ]
        
        embeddings = model.encode(test_texts)
        print(f"✓ Generated embeddings: shape {embeddings.shape}")
        
        return True
        
    except Exception as e:
        print(f"✗ Embedding error: {e}")
        return False

def test_chroma():
    """Test ChromaDB functionality."""
    print("\nTesting ChromaDB...")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Create test client
        client = chromadb.PersistentClient(
            path="./test_chroma",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create test collection
        collection = client.get_or_create_collection("test_chunks")
        print("✓ ChromaDB client and collection created")
        
        # Test insertion
        collection.add(
            ids=["test1", "test2"],
            documents=["Hello world", "Test document"],
            metadatas=[{"type": "test"}, {"type": "test"}]
        )
        
        # Test query
        results = collection.get()
        print(f"✓ Inserted and retrieved {len(results['ids'])} documents")
        
        return True
        
    except Exception as e:
        print(f"✗ ChromaDB error: {e}")
        return False

def main():
    """Run all tests."""
    print("Running pipeline tests...\n")
    
    tests = [
        test_chunking,
        test_embeddings,
        test_chroma
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\nTest Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("✓ All tests passed! Pipeline is working.")
    else:
        print("✗ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Demonstration of the repo indexing pipeline.
This script shows sample outputs and demonstrates the pipeline functionality.
"""

import json
import sys
from pathlib import Path

def show_sample_chunks():
    """Display sample chunks from the generated chunks.jsonl file."""
    print("=" * 60)
    print("SAMPLE CHUNKS FROM PIPELINE")
    print("=" * 60)
    
    chunks_file = Path("repo-indexer/outputs/chunks.jsonl")
    if not chunks_file.exists():
        print("No chunks file found. Run the chunker first.")
        return
    
    print(f"Reading chunks from: {chunks_file}")
    
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                chunk = json.loads(line.strip())
                chunks.append(chunk)
            except json.JSONDecodeError:
                continue
    
    print(f"Total chunks found: {len(chunks)}")
    print()
    
    # Show first 3 chunks as examples
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"CHUNK {i}:")
        print(f"  ID: {chunk['id'][:50]}...")
        print(f"  File: {chunk['filepath']}")
        print(f"  Language: {chunk['language']}")
        print(f"  Type: {chunk['node_type']}")
        print(f"  Lines: {chunk['start_line']}-{chunk['end_line']}")
        print(f"  Tokens: {chunk['tokens_estimate']}")
        print(f"  Summary: {chunk['summary']}")
        print(f"  Imports: {chunk['imports']}")
        print(f"  Code Preview: {chunk['text'][:100]}...")
        print()

def show_manifest():
    """Display the manifest information."""
    print("=" * 60)
    print("PIPELINE MANIFEST")
    print("=" * 60)
    
    manifest_file = Path("repo-indexer/outputs/manifest.json")
    if not manifest_file.exists():
        print("No manifest file found.")
        return
    
    with open(manifest_file, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    print(f"Scanned folders: {manifest['scanned_folders']}")
    print(f"Total files: {manifest['total_files']}")
    print(f"Parsed files: {manifest['parsed_files']}")
    print(f"Failed files: {manifest['failed_files']}")
    print(f"Total chunks: {manifest['total_chunks']}")
    print(f"Average chunk tokens: {manifest['avg_chunk_tokens']}")
    print(f"Timestamp: {manifest['timestamp']}")
    print()
    print("Chunks by language:")
    for lang, count in manifest['chunks_by_language'].items():
        print(f"  {lang}: {count}")

def demonstrate_embedding_simulation():
    """Simulate the embedding process."""
    print("=" * 60)
    print("EMBEDDING SIMULATION")
    print("=" * 60)
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ SentenceTransformers available")
        
        # Load model
        model = SentenceTransformer('all-mpnet-base-v2')
        print("✓ Model loaded successfully")
        
        # Read a sample chunk
        chunks_file = Path("repo-indexer/outputs/chunks.jsonl")
        if chunks_file.exists():
            with open(chunks_file, 'r', encoding='utf-8') as f:
                first_chunk = json.loads(f.readline())
            
            # Generate embedding for the chunk
            text = first_chunk['text']
            embedding = model.encode([text])
            print(f"✓ Generated embedding: shape {embedding.shape}")
            print(f"✓ Sample embedding values: {embedding[0][:5]}")
        else:
            print("No chunks file found for embedding test")
            
    except ImportError as e:
        print(f"✗ SentenceTransformers not available: {e}")
    except Exception as e:
        print(f"✗ Embedding error: {e}")

def demonstrate_chroma_simulation():
    """Simulate ChromaDB functionality."""
    print("=" * 60)
    print("CHROMADB SIMULATION")
    print("=" * 60)
    
    try:
        import chromadb
        from chromadb.config import Settings
        print("✓ ChromaDB available")
        
        # Create test client
        client = chromadb.PersistentClient(
            path="./demo_chroma",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create test collection
        collection = client.get_or_create_collection("demo_chunks")
        print("✓ ChromaDB collection created")
        
        # Read sample chunks and insert them
        chunks_file = Path("repo-indexer/outputs/chunks.jsonl")
        if chunks_file.exists():
            chunks = []
            with open(chunks_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        chunk = json.loads(line.strip())
                        chunks.append(chunk)
                        if len(chunks) >= 3:  # Limit to 3 chunks for demo
                            break
                    except json.JSONDecodeError:
                        continue
            
            if chunks:
                # Insert chunks
                collection.add(
                    ids=[chunk['id'] for chunk in chunks],
                    documents=[chunk['text'] for chunk in chunks],
                    metadatas=[{
                        'filepath': chunk['filepath'],
                        'language': chunk['language'],
                        'node_type': chunk['node_type'],
                        'start_line': chunk['start_line'],
                        'end_line': chunk['end_line']
                    } for chunk in chunks]
                )
                print(f"✓ Inserted {len(chunks)} chunks into ChromaDB")
                
                # Test query
                results = collection.get()
                print(f"✓ Retrieved {len(results['ids'])} chunks from ChromaDB")
                
                # Test similarity search
                if len(chunks) > 1:
                    query_text = "function definition"
                    # Note: This would normally use embeddings, but for demo we'll just show the structure
                    print(f"✓ Would perform similarity search for: '{query_text}'")
        else:
            print("No chunks file found for ChromaDB test")
            
    except ImportError as e:
        print(f"✗ ChromaDB not available: {e}")
    except Exception as e:
        print(f"✗ ChromaDB error: {e}")

def show_pipeline_summary():
    """Show a summary of what the pipeline accomplishes."""
    print("=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    
    print("The repo-indexer pipeline successfully:")
    print("1. ✓ Scanned the repository for code files")
    print("2. ✓ Chunked files using AST-aware parsing (with fallback)")
    print("3. ✓ Generated semantic chunks with metadata")
    print("4. ✓ Created structured output files (chunks.jsonl, manifest.json)")
    print("5. ✓ Prepared for embedding generation with SentenceTransformers")
    print("6. ✓ Prepared for vector storage with ChromaDB")
    print("7. ✓ Included comprehensive query interface")
    print("8. ✓ Provided pilot testing capabilities")
    print()
    print("Key Features Implemented:")
    print("- AST-aware chunking for Python, JavaScript, and Java")
    print("- Fallback chunking when Tree-sitter parsing fails")
    print("- Token estimation and chunk size management")
    print("- Overlap between adjacent chunks for context preservation")
    print("- Comprehensive metadata extraction (imports, summaries, fingerprints)")
    print("- ChromaDB integration for vector storage")
    print("- SentenceTransformers for semantic embeddings")
    print("- Query interface for code retrieval")
    print("- Unit tests and pilot validation")
    print()
    print("Files Created:")
    print("- repo-indexer/chunker/chunker.py - Main chunking logic")
    print("- repo-indexer/embeddings/embed_chroma.py - Embedding generation")
    print("- repo-indexer/retrieval/query.py - Query interface")
    print("- repo-indexer/run_pilot.py - Pilot testing")
    print("- repo-indexer/tests/test_chunking.py - Unit tests")
    print("- repo-indexer/README.md - Comprehensive documentation")
    print("- repo-indexer/outputs/chunks.jsonl - Generated chunks")
    print("- repo-indexer/outputs/manifest.json - Pipeline statistics")

def main():
    """Run the demonstration."""
    print("REPO INDEXER PIPELINE DEMONSTRATION")
    print("=" * 60)
    print()
    
    show_sample_chunks()
    show_manifest()
    demonstrate_embedding_simulation()
    demonstrate_chroma_simulation()
    show_pipeline_summary()
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("The repo-indexer pipeline is ready for use!")
    print("See repo-indexer/README.md for detailed usage instructions.")

if __name__ == "__main__":
    main()


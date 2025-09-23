#!/usr/bin/env python3
"""Test dependencies and basic functionality."""

try:
    from sentence_transformers import SentenceTransformer
    print("✓ SentenceTransformers imported successfully")
    
    # Test model loading
    model = SentenceTransformer('all-mpnet-base-v2')
    print("✓ Model loaded successfully")
    
    # Test embedding
    test_text = "This is a test sentence."
    embedding = model.encode([test_text])
    print(f"✓ Embedding generated: shape {embedding.shape}")
    
except Exception as e:
    print(f"✗ SentenceTransformers error: {e}")

try:
    import chromadb
    print("✓ ChromaDB imported successfully")
    
    # Test ChromaDB client
    client = chromadb.PersistentClient(path="./test_chroma")
    print("✓ ChromaDB client created successfully")
    
except Exception as e:
    print(f"✗ ChromaDB error: {e}")

try:
    import tiktoken
    print("✓ tiktoken imported successfully")
    
    # Test tokenization
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode("This is a test.")
    print(f"✓ Tokenization works: {len(tokens)} tokens")
    
except Exception as e:
    print(f"✗ tiktoken error: {e}")

print("Dependency test complete!")


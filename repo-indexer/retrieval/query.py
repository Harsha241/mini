#!/usr/bin/env python3
"""
Query interface for retrieving code chunks from ChromaDB.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class CodeRetriever:
    """Code chunk retrieval from ChromaDB."""
    
    def __init__(self, chroma_path: str = "./repo-indexer/chroma_store", 
                 model_name: str = "all-mpnet-base-v2"):
        self.chroma_path = chroma_path
        self.model_name = model_name
        self.client = None
        self.collection = None
        self.model = None
        
        self._setup_logging()
        self._setup_model()
        self._setup_chroma()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    
    def _setup_model(self):
        """Setup SentenceTransformer model."""
        if not SentenceTransformer:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        
        try:
            self.model = SentenceTransformer(self.model_name)
            logging.info(f"Loaded model: {self.model_name}")
        except Exception as e:
            logging.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def _setup_chroma(self):
        """Setup ChromaDB client and collection."""
        if not chromadb:
            raise ImportError("chromadb not installed. Run: pip install chromadb")
        
        try:
            # Connect to persistent client
            self.client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get collection
            self.collection = self.client.get_collection("repo_chunks")
            logging.info(f"Connected to ChromaDB at {self.chroma_path}")
        except Exception as e:
            logging.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding to float32."""
        import numpy as np
        embedding_array = np.array(embedding, dtype=np.float32)
        # L2 normalize
        norm = np.linalg.norm(embedding_array)
        if norm > 0:
            embedding_array = embedding_array / norm
        return embedding_array.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for query text."""
        try:
            embedding = self.model.encode([query], convert_to_tensor=False)[0]
            return self._normalize_embedding(embedding.tolist())
        except Exception as e:
            logging.error(f"Error generating query embedding: {e}")
            raise
    
    def search(self, query: str, n_results: int = 5, 
               where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar code chunks."""
        try:
            # Generate query embedding
            query_embedding = self.embed_query(query)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': 1 - results['distances'][0][i]  # Convert distance to similarity
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error searching: {e}")
            raise
    
    def search_by_language(self, query: str, language: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for chunks in a specific language."""
        where_clause = {"language": language}
        return self.search(query, n_results, where_clause)
    
    def search_by_file(self, query: str, filepath: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for chunks in a specific file."""
        where_clause = {"filepath": filepath}
        return self.search(query, n_results, where_clause)
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by ID."""
        try:
            results = self.collection.get(
                ids=[chunk_id],
                include=['documents', 'metadatas']
            )
            
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logging.error(f"Error getting chunk {chunk_id}: {e}")
            return None
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            count = self.collection.count()
            
            # Get sample of metadata to understand structure
            sample = self.collection.get(limit=1, include=['metadatas'])
            languages = set()
            if sample['metadatas']:
                for metadata in sample['metadatas']:
                    if 'language' in metadata:
                        languages.add(metadata['language'])
            
            return {
                'total_chunks': count,
                'collection_name': 'repo_chunks',
                'model_name': self.model_name,
                'languages': list(languages)
            }
        except Exception as e:
            logging.error(f"Error getting collection info: {e}")
            return {'error': str(e)}


def format_results(results: List[Dict[str, Any]], format_type: str = "json") -> str:
    """Format search results for output."""
    if format_type == "json":
        return json.dumps(results, indent=2)
    elif format_type == "text":
        output = []
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            output.append(f"Result {i}:")
            output.append(f"  File: {metadata.get('filepath', 'Unknown')}")
            output.append(f"  Language: {metadata.get('language', 'Unknown')}")
            output.append(f"  Type: {metadata.get('node_type', 'Unknown')}")
            output.append(f"  Lines: {metadata.get('start_line', '?')}-{metadata.get('end_line', '?')}")
            output.append(f"  Similarity: {result['similarity_score']:.4f}")
            output.append(f"  Summary: {metadata.get('summary', 'No summary')}")
            output.append(f"  Code:\n{result['document'][:200]}...")
            output.append("")
        return "\n".join(output)
    else:
        return str(results)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Query code chunks from ChromaDB")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--n", type=int, default=5, help="Number of results to return")
    parser.add_argument("--chroma-path", default="./repo-indexer/chroma_store",
                       help="Path to ChromaDB storage")
    parser.add_argument("--model", default="all-mpnet-base-v2",
                       help="SentenceTransformer model name")
    parser.add_argument("--language", help="Filter by programming language")
    parser.add_argument("--filepath", help="Filter by file path")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                       help="Output format")
    
    args = parser.parse_args()
    
    # Override with environment variables
    model_name = os.getenv('SENTENCE_MODEL', args.model)
    chroma_path = os.getenv('CHROMA_PATH', args.chroma_path)
    
    try:
        retriever = CodeRetriever(
            chroma_path=chroma_path,
            model_name=model_name
        )
        
        # Perform search
        if args.language:
            results = retriever.search_by_language(args.query, args.language, args.n)
        elif args.filepath:
            results = retriever.search_by_file(args.query, args.filepath, args.n)
        else:
            results = retriever.search(args.query, args.n)
        
        # Format and print results
        output = format_results(results, args.format)
        print(output)
        
        # Print collection info
        info = retriever.get_collection_info()
        if 'error' not in info:
            print(f"\nCollection Info:")
            print(f"Total chunks: {info.get('total_chunks', 'Unknown')}")
            print(f"Languages: {', '.join(info.get('languages', []))}")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Generate embeddings for code chunks using SentenceTransformers and store in ChromaDB.
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


class ChromaEmbedder:
    """ChromaDB-based embedding storage and retrieval."""
    
    def __init__(self, chroma_path: str = "./repo-indexer/chroma_store", 
                 model_name: str = "all-mpnet-base-v2", batch_size: int = 64):
        self.chroma_path = chroma_path
        self.model_name = model_name
        self.batch_size = batch_size
        self.client = None
        self.collection = None
        self.model = None
        self.errors = []
        
        self._setup_logging()
        self._setup_model()
        self._setup_chroma()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = Path("repo-indexer/outputs/pipeline_errors.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
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
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="repo_chunks",
                metadata={"description": "Code repository chunks with embeddings"}
            )
            
            logging.info(f"Connected to ChromaDB at {self.chroma_path}")
        except Exception as e:
            logging.error(f"Failed to setup ChromaDB: {e}")
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
    
    def _check_existing_chunk(self, chunk_id: str, code_fingerprint: str) -> bool:
        """Check if chunk already exists with same fingerprint."""
        try:
            result = self.collection.get(ids=[chunk_id])
            if result['ids']:
                # Check if fingerprint matches
                metadata = result['metadatas'][0]
                existing_fingerprint = metadata.get('code_fingerprint', '')
                return existing_fingerprint == code_fingerprint
        except Exception as e:
            logging.warning(f"Error checking existing chunk {chunk_id}: {e}")
        return False
    
    def embed_batch(self, chunks: List[Dict]) -> List[List[float]]:
        """Generate embeddings for a batch of chunks."""
        texts = [chunk['text'] for chunk in chunks]
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
            
            # Normalize embeddings
            normalized_embeddings = []
            for embedding in embeddings:
                normalized_embeddings.append(self._normalize_embedding(embedding.tolist()))
            
            return normalized_embeddings
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            self.errors.append(f"Embedding generation failed: {e}")
            return []
    
    def insert_batch(self, chunks: List[Dict], embeddings: List[List[float]], force: bool = False):
        """Insert a batch of chunks with embeddings into ChromaDB."""
        if not embeddings:
            return
        
        ids = []
        documents = []
        metadatas = []
        embeddings_to_insert = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = chunk['id']
            code_fingerprint = chunk['code_fingerprint']
            
            # Check if chunk already exists (unless force)
            if not force and self._check_existing_chunk(chunk_id, code_fingerprint):
                logging.debug(f"Skipping existing chunk: {chunk_id}")
                continue
            
            ids.append(chunk_id)
            documents.append(chunk['text'])
            metadatas.append({
                'filepath': chunk['filepath'],
                'language': chunk['language'],
                'node_type': chunk['node_type'],
                'start_line': chunk['start_line'],
                'end_line': chunk['end_line'],
                'summary': chunk['summary'],
                'code_fingerprint': code_fingerprint,
                'last_modified': chunk['last_modified'],
                'tokens_estimate': chunk['tokens_estimate']
            })
            embeddings_to_insert.append(embeddings[i])
        
        if not ids:
            logging.info("No new chunks to insert")
            return
        
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_to_insert
            )
            logging.info(f"Inserted {len(ids)} chunks into ChromaDB")
        except Exception as e:
            logging.error(f"Error inserting batch: {e}")
            self.errors.append(f"ChromaDB insertion failed: {e}")
    
    def process_chunks_file(self, chunks_file: str, force: bool = False, dry_run: bool = False):
        """Process chunks from JSONL file."""
        chunks_file = Path(chunks_file)
        if not chunks_file.exists():
            raise FileNotFoundError(f"Chunks file not found: {chunks_file}")
        
        logging.info(f"Processing chunks from {chunks_file}")
        
        chunks = []
        total_processed = 0
        total_inserted = 0
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    chunk = json.loads(line.strip())
                    chunks.append(chunk)
                    
                    # Process in batches
                    if len(chunks) >= self.batch_size:
                        if not dry_run:
                            embeddings = self.embed_batch(chunks)
                            if embeddings:
                                self.insert_batch(chunks, embeddings, force)
                                total_inserted += len([c for c in chunks if c['id'] not in []]])
                        else:
                            logging.info(f"DRY RUN: Would process batch of {len(chunks)} chunks")
                            total_inserted += len(chunks)
                        
                        total_processed += len(chunks)
                        chunks = []
                        
                        if total_processed % (self.batch_size * 10) == 0:
                            logging.info(f"Processed {total_processed} chunks...")
                
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error at line {line_num}: {e}")
                    self.errors.append(f"JSON decode error at line {line_num}: {e}")
                except Exception as e:
                    logging.error(f"Error processing line {line_num}: {e}")
                    self.errors.append(f"Error processing line {line_num}: {e}")
        
        # Process remaining chunks
        if chunks:
            if not dry_run:
                embeddings = self.embed_batch(chunks)
                if embeddings:
                    self.insert_batch(chunks, embeddings, force)
                    total_inserted += len([c for c in chunks if c['id'] not in []]])
            else:
                logging.info(f"DRY RUN: Would process final batch of {len(chunks)} chunks")
                total_inserted += len(chunks)
            
            total_processed += len(chunks)
        
        logging.info(f"Processing complete. Total processed: {total_processed}, Total inserted: {total_inserted}")
        
        if self.errors:
            logging.warning(f"Encountered {len(self.errors)} errors during processing")
            for error in self.errors:
                logging.warning(f"Error: {error}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": "repo_chunks",
                "model_name": self.model_name
            }
        except Exception as e:
            logging.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate embeddings for code chunks")
    parser.add_argument("--chunks", default="repo-indexer/outputs/chunks.jsonl", 
                       help="Path to chunks JSONL file")
    parser.add_argument("--chroma-path", default="./repo-indexer/chroma_store",
                       help="Path to ChromaDB storage")
    parser.add_argument("--batch-size", type=int, default=64,
                       help="Batch size for embedding generation")
    parser.add_argument("--model", default="all-mpnet-base-v2",
                       help="SentenceTransformer model name")
    parser.add_argument("--force", action="store_true",
                       help="Force re-embedding of existing chunks")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run mode")
    
    args = parser.parse_args()
    
    # Override with environment variables
    model_name = os.getenv('SENTENCE_MODEL', args.model)
    chroma_path = os.getenv('CHROMA_PATH', args.chroma_path)
    
    try:
        embedder = ChromaEmbedder(
            chroma_path=chroma_path,
            model_name=model_name,
            batch_size=args.batch_size
        )
        
        embedder.process_chunks_file(
            chunks_file=args.chunks,
            force=args.force,
            dry_run=args.dry_run
        )
        
        # Print collection stats
        stats = embedder.get_collection_stats()
        print(f"\nCollection Statistics:")
        print(f"Total chunks: {stats.get('total_chunks', 'Unknown')}")
        print(f"Model: {stats.get('model_name', 'Unknown')}")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


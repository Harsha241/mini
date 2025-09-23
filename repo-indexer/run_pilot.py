#!/usr/bin/env python3
"""
Pilot script to test the repo indexing pipeline.
"""

import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add modules to path
sys.path.append(str(Path(__file__).parent))

from embeddings.embed_chroma import ChromaEmbedder
from retrieval.query import CodeRetriever


class PilotRunner:
    """Run pilot tests on the indexing pipeline."""
    
    def __init__(self, chunks_file: str = "repo-indexer/outputs/chunks.jsonl",
                 chroma_path: str = "./repo-indexer/chroma_store",
                 model_name: str = "all-mpnet-base-v2"):
        self.chunks_file = Path(chunks_file)
        self.chroma_path = chroma_path
        self.model_name = model_name
        self.output_dir = Path("repo-indexer/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    
    def load_chunks(self) -> List[Dict[str, Any]]:
        """Load chunks from JSONL file."""
        if not self.chunks_file.exists():
            raise FileNotFoundError(f"Chunks file not found: {self.chunks_file}")
        
        chunks = []
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    chunk = json.loads(line.strip())
                    chunks.append(chunk)
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed to parse chunk: {e}")
        
        logging.info(f"Loaded {len(chunks)} chunks from {self.chunks_file}")
        return chunks
    
    def select_pilot_chunks(self, chunks: List[Dict[str, Any]], n_samples: int = 50) -> List[Dict[str, Any]]:
        """Select representative chunks for pilot testing."""
        if len(chunks) <= n_samples:
            return chunks
        
        # Group chunks by language
        by_language = {}
        for chunk in chunks:
            lang = chunk.get('language', 'unknown')
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(chunk)
        
        # Sample from each language proportionally
        selected = []
        total_chunks = len(chunks)
        
        for lang, lang_chunks in by_language.items():
            # Calculate proportional sample size
            lang_ratio = len(lang_chunks) / total_chunks
            lang_sample_size = max(1, int(n_samples * lang_ratio))
            
            # Sample chunks with size diversity
            lang_chunks_sorted = sorted(lang_chunks, key=lambda x: x.get('tokens_estimate', 0))
            
            # Take small, medium, and large chunks
            small_chunks = [c for c in lang_chunks_sorted if c.get('tokens_estimate', 0) < 1000]
            medium_chunks = [c for c in lang_chunks_sorted if 1000 <= c.get('tokens_estimate', 0) < 5000]
            large_chunks = [c for c in lang_chunks_sorted if c.get('tokens_estimate', 0) >= 5000]
            
            # Sample from each size category
            sample_size = lang_sample_size
            selected_from_lang = []
            
            if small_chunks and sample_size > 0:
                selected_from_lang.extend(random.sample(small_chunks, min(len(small_chunks), sample_size // 3)))
                sample_size -= len(selected_from_lang)
            
            if medium_chunks and sample_size > 0:
                selected_from_lang.extend(random.sample(medium_chunks, min(len(medium_chunks), sample_size // 2)))
                sample_size -= len(selected_from_lang) - len([c for c in selected_from_lang if c in small_chunks])
            
            if large_chunks and sample_size > 0:
                selected_from_lang.extend(random.sample(large_chunks, min(len(large_chunks), sample_size)))
            
            selected.extend(selected_from_lang)
        
        # If we don't have enough, fill with random samples
        if len(selected) < n_samples:
            remaining = [c for c in chunks if c not in selected]
            additional = random.sample(remaining, min(len(remaining), n_samples - len(selected)))
            selected.extend(additional)
        
        # Limit to requested number
        selected = selected[:n_samples]
        
        logging.info(f"Selected {len(selected)} pilot chunks from {len(chunks)} total chunks")
        return selected
    
    def run_pilot_embedding(self, pilot_chunks: List[Dict[str, Any]]) -> ChromaEmbedder:
        """Run embedding process on pilot chunks."""
        logging.info("Starting pilot embedding process...")
        
        # Create temporary chunks file for pilot
        pilot_chunks_file = self.output_dir / "pilot_chunks.jsonl"
        with open(pilot_chunks_file, 'w', encoding='utf-8') as f:
            for chunk in pilot_chunks:
                # Add pilot tag to metadata
                chunk['pilot'] = True
                f.write(json.dumps(chunk) + '\n')
        
        # Initialize embedder
        embedder = ChromaEmbedder(
            chroma_path=self.chroma_path,
            model_name=self.model_name,
            batch_size=32  # Smaller batch for pilot
        )
        
        # Process pilot chunks
        embedder.process_chunks_file(str(pilot_chunks_file), force=True)
        
        logging.info("Pilot embedding complete")
        return embedder
    
    def run_pilot_query(self, query: str = "how is authentication implemented?") -> List[Dict[str, Any]]:
        """Run pilot query and return results."""
        logging.info(f"Running pilot query: '{query}'")
        
        # Initialize retriever
        retriever = CodeRetriever(
            chroma_path=self.chroma_path,
            model_name=self.model_name
        )
        
        # Search for results
        results = retriever.search(query, n_results=5)
        
        logging.info(f"Found {len(results)} results for query")
        return results
    
    def save_pilot_results(self, results: List[Dict[str, Any]], query: str):
        """Save pilot results to file."""
        pilot_results = {
            'query': query,
            'timestamp': str(Path().cwd()),
            'total_results': len(results),
            'results': results
        }
        
        results_file = self.output_dir / "pilot_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(pilot_results, f, indent=2)
        
        logging.info(f"Pilot results saved to {results_file}")
    
    def print_pilot_report(self, results: List[Dict[str, Any]], query: str):
        """Print pilot report to console."""
        print("\n" + "="*60)
        print("PILOT TEST REPORT")
        print("="*60)
        print(f"Query: '{query}'")
        print(f"Results found: {len(results)}")
        print()
        
        if not results:
            print("No results found. This could indicate:")
            print("- No relevant code chunks in the repository")
            print("- Embedding model not suitable for the codebase")
            print("- ChromaDB not properly populated")
            return
        
        print("Top Results:")
        print("-" * 40)
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            similarity = result['similarity_score']
            
            print(f"\n{i}. {metadata.get('filepath', 'Unknown file')}")
            print(f"   Language: {metadata.get('language', 'Unknown')}")
            print(f"   Type: {metadata.get('node_type', 'Unknown')}")
            print(f"   Lines: {metadata.get('start_line', '?')}-{metadata.get('end_line', '?')}")
            print(f"   Similarity: {similarity:.4f}")
            print(f"   Summary: {metadata.get('summary', 'No summary')}")
            
            # Show code snippet
            code = result['document']
            if len(code) > 200:
                code = code[:200] + "..."
            print(f"   Code: {code}")
        
        print("\n" + "="*60)
    
    def run(self):
        """Run the complete pilot test."""
        try:
            # Load chunks
            chunks = self.load_chunks()
            if not chunks:
                print("No chunks found. Run the chunker first.")
                return
            
            # Select pilot chunks
            pilot_chunks = self.select_pilot_chunks(chunks, n_samples=50)
            
            # Run embedding
            embedder = self.run_pilot_embedding(pilot_chunks)
            
            # Run query
            query = "how is authentication implemented?"
            results = self.run_pilot_query(query)
            
            # Save results
            self.save_pilot_results(results, query)
            
            # Print report
            self.print_pilot_report(results, query)
            
            # Print collection stats
            stats = embedder.get_collection_stats()
            print(f"\nCollection Statistics:")
            print(f"Total chunks in collection: {stats.get('total_chunks', 'Unknown')}")
            print(f"Model used: {stats.get('model_name', 'Unknown')}")
            
        except Exception as e:
            logging.error(f"Pilot test failed: {e}")
            raise


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run pilot test for repo indexing pipeline")
    parser.add_argument("--chunks", default="repo-indexer/outputs/chunks.jsonl",
                       help="Path to chunks JSONL file")
    parser.add_argument("--chroma-path", default="./repo-indexer/chroma_store",
                       help="Path to ChromaDB storage")
    parser.add_argument("--model", default="all-mpnet-base-v2",
                       help="SentenceTransformer model name")
    parser.add_argument("--query", default="how is authentication implemented?",
                       help="Test query to run")
    
    args = parser.parse_args()
    
    pilot = PilotRunner(
        chunks_file=args.chunks,
        chroma_path=args.chroma_path,
        model_name=args.model
    )
    
    pilot.run()


if __name__ == "__main__":
    main()


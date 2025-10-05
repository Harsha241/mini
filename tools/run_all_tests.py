#!/usr/bin/env python3
"""
Automated test runner for the project.
Installs minimal runtime deps if missing, runs chunking, embeddings (dry-run),
retrieval query, and existing test scripts. Saves a summary report with logs.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict


def run_cmd(cmd: List[str], env: Dict[str, str] | None = None, cwd: str | None = None) -> Dict[str, str | int]:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env or os.environ.copy(),
        cwd=cwd or str(Path.cwd()),
    )
    output_lines: List[str] = []
    for line in proc.stdout:  # type: ignore[attr-defined]
        print(line, end="")
        output_lines.append(line)
    proc.wait()
    return {"returncode": proc.returncode, "output": "".join(output_lines)}


def ensure_min_deps(python_exe: str) -> None:
    cmd = [python_exe, "-m", "pip", "install", "--disable-pip-version-check", "sentence-transformers", "chromadb"]
    run_cmd(cmd)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run all project tests and demos")
    parser.add_argument("--root", required=True, help="Directory to index for chunking")
    parser.add_argument("--out", default="repo-indexer/outputs", help="Output directory for chunks")
    parser.add_argument("--chroma", default="repo-indexer/chroma_store", help="ChromaDB storage path")
    parser.add_argument("--query", default="how is authentication implemented?", help="Sample retrieval query")
    parser.add_argument("--full-embed", action="store_true", help="Run full embeddings (not dry-run)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    venv_python = project_root / "venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python if venv_python.exists() else sys.executable)

    report_dir = project_root / "test_outputs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {"steps": []}

    # Step 0: Ensure minimal deps
    step = {"name": "install_deps"}
    try:
        ensure_min_deps(python_exe)
        step["status"] = "ok"
    except Exception as e:
        step["status"] = "error"
        step["error"] = str(e)
    report["steps"].append(step)

    # Step 1: Run dependency smoke test
    step = {"name": "test_deps"}
    res = run_cmd([python_exe, "test_deps.py"])
    step["status"] = "ok" if res["returncode"] == 0 else "fail"
    step["returncode"] = res["returncode"]
    step["log"] = res["output"]
    report["steps"].append(step)

    # Step 2: Chunking
    step = {"name": "chunking"}
    res = run_cmd([python_exe, "-m", "repo_indexer.chunker.chunker", "--root", args.root, "--out", args.out])
    step["status"] = "ok" if res["returncode"] == 0 else "fail"
    step["returncode"] = res["returncode"]
    step["log"] = res["output"]
    report["steps"].append(step)

    chunks_file = str(Path(args.out) / "chunks.jsonl")

    # Step 3: Embeddings (dry-run by default)
    step = {"name": "embeddings_dry_run" if not args.full_embed else "embeddings_full"}
    embed_cmd = [python_exe, "-m", "repo_indexer.embeddings.embed_chroma", "--chunks", chunks_file, "--chroma-path", args.chroma]
    if not args.full_embed:
        embed_cmd.append("--dry-run")
    res = run_cmd(embed_cmd)
    step["status"] = "ok" if res["returncode"] == 0 else "fail"
    step["returncode"] = res["returncode"]
    step["log"] = res["output"]
    report["steps"].append(step)

    # Step 4: Retrieval (may be empty if not embedded)
    step = {"name": "retrieval_query"}
    res = run_cmd([python_exe, "-m", "repo_indexer.retrieval.query", "--query", args.query, "--chroma-path", args.chroma, "--format", "text"])
    step["status"] = "ok" if res["returncode"] == 0 else "fail"
    step["returncode"] = res["returncode"]
    step["log"] = res["output"]
    report["steps"].append(step)

    # Save report
    report_path = report_dir / "run_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nSummary written to {report_path}")


if __name__ == "__main__":
    main()



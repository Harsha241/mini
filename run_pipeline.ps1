# Purpose: One-command runner to chunk a repo and embed chunks into ChromaDB.
# Prompts for input repo path, output dir, and Chroma path, then executes steps.
# Usage: PowerShell -ExecutionPolicy Bypass -File run_pipeline.ps1

param(
    [string]$RootPath = "",
    [string]$OutputDir = "repo-indexer/outputs",
    [string]$ChromaPath = "repo-indexer/chroma_store",
    [string]$SentenceModel = "all-mpnet-base-v2"
)

function Prompt-IfEmpty($value, $message) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        return Read-Host $message
    }
    return $value
}

# Ensure venv python if available
$python = "python"
$venvPython = Join-Path -Path ".\venv\Scripts" -ChildPath "python.exe"
if (Test-Path $venvPython) { $python = $venvPython }

$RootPath = Prompt-IfEmpty $RootPath "Enter directory to index (absolute or relative path)"
if (-not (Test-Path $RootPath)) { Write-Error "Path not found: $RootPath"; exit 1 }

$OutputDir = Prompt-IfEmpty $OutputDir "Enter output directory for chunks (default: repo-indexer/outputs)"
$ChromaPath = Prompt-IfEmpty $ChromaPath "Enter Chroma storage directory (default: repo-indexer/chroma_store)"

Write-Host "[1/3] Chunking repository..." -ForegroundColor Cyan
& $python -m repo_indexer.chunker.chunker --root "$RootPath" --out "$OutputDir"
if ($LASTEXITCODE -ne 0) { Write-Error "Chunking failed."; exit 1 }

$chunksFile = Join-Path $OutputDir "chunks.jsonl"
if (-not (Test-Path $chunksFile)) { Write-Error "Chunks file not found at $chunksFile"; exit 1 }

Write-Host "[2/3] Generating embeddings and populating ChromaDB..." -ForegroundColor Cyan
$env:SENTENCE_MODEL = $SentenceModel
$env:CHROMA_PATH = $ChromaPath
& $python -m repo_indexer.embeddings.embed_chroma --chunks "$chunksFile" --chroma-path "$ChromaPath"
if ($LASTEXITCODE -ne 0) { Write-Error "Embedding failed."; exit 1 }

Write-Host "[3/3] Running a sample query..." -ForegroundColor Cyan
& $python -m repo_indexer.retrieval.query --query "how is authentication implemented?" --chroma-path "$ChromaPath" --format text
if ($LASTEXITCODE -ne 0) { Write-Warning "Sample query failed; continuing." }

Write-Host "Pipeline complete." -ForegroundColor Green

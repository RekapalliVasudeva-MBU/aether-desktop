# Ollama Partial Download Cleanup

When `ollama pull` fails (TLS timeout, network error, etc.), Ollama leaves incomplete blob files in `~/.ollama/models/blobs/` named `*-partial*`. These can be 5-10 GB per failed model.

## Detection

Write as `.ps1` file (never inline in bash/MSYS):

```powershell
$blobs = "$env:USERPROFILE\.ollama\models\blobs"
$partials = Get-ChildItem $blobs -Recurse -File | Where-Object { $_.Name -like "*-partial*" }
$totalMB = ($partials | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Output "Found $($partials.Count) partial files, $([math]::Round($totalMB,1)) MB total"
$partials | ForEach-Object { Write-Output "  $($_.Name) => $([math]::Round($_.Length/1MB,1)) MB" }
```

## Cleanup

```powershell
$blobs = "$env:USERPROFILE\.ollama\models\blobs"
$deleted = 0
Get-ChildItem $blobs -Recurse -File | Where-Object { $_.Name -like "*-partial*" } | ForEach-Object {
    Write-Output "Deleting: $($_.Name) => $([math]::Round($_.Length/1MB,1)) MB"
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    $deleted++
}
# Remove empty directories left behind
Get-ChildItem $blobs -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue).Count -eq 0 } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Output "Deleted $deleted files"
```

## Common Causes of Failed Downloads

- **TLS handshake timeout**: Network blocks Cloudflare R2 (where Ollama stores models). Suggest VPN.
- **Connection reset**: Unstable network. Retry with `ollama pull <model>`.
- **Disk full**: Check free space before pulling large models.

## Prevention

- Always ask the user before running `ollama pull` (see llama-cpp skill)
- Check available disk space first
- Warn the user that a failed download may leave partial files that need cleanup

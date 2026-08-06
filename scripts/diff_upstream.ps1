$ErrorActionPreference = "Continue"
$up = "E:\notebook\_upstream_ref\open-notebook-main"
$ours = "E:\notebook\open-notebook"

$files = @(
    "api/repository.py",
    "api/security.py",
    "open_notebook/domain/base.py",
    "pyproject.toml",
    "open_notebook/utils/logger.py",
    "api/sources_service.py",
    "open_notebook/domain/notebook.py",
    "api/main.py",
    "api/routers/sources.py",
    "api/routers/credentials.py",
    "open_notebook/ai/provider_registry.py",
    "open_notebook/ai/key_provider.py",
    "open_notebook/ai/models.py",
    "api/mcp_server.py",
    "open_notebook/domain/source.py"
)

foreach ($f in $files) {
    $oursPath = Join-Path $ours $f
    $theirPath = Join-Path $up $f
    $status = "?"
    if ((Test-Path $oursPath) -and (Test-Path $theirPath)) {
        $oursHash = (Get-FileHash $oursPath -Algorithm MD5).Hash
        $theirHash = (Get-FileHash $theirPath -Algorithm MD5).Hash
        if ($oursHash -eq $theirHash) { $status = "SAME" }
        else {
            $oursLen = (Get-Item $oursPath).Length
            $theirLen = (Get-Item $theirPath).Length
            $status = "DIFF (ours=$oursLen theirs=$theirLen)"
        }
    } elseif (Test-Path $theirPath) { $status = "NEW-UPSTREAM" }
    elseif (Test-Path $oursPath) { $status = "OURS-ONLY" }
    Write-Output "${f} : $status"
}

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$app = Resolve-Path (Join-Path $PSScriptRoot "..")
$dist = Join-Path $repo "dist"
$bundle = Join-Path $dist "LocalAgentAppFactory"
$zip = Join-Path $dist "LocalAgentAppFactory.zip"
if (!(Test-Path $dist)) { New-Item -ItemType Directory -Path $dist -Force | Out-Null }
if (Test-Path $bundle) { Remove-Item -Path $bundle -Recurse -Force }
if (Test-Path $zip) { Remove-Item -Path $zip -Force }
New-Item -ItemType Directory -Path $bundle -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundle "app") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundle "runtime\codefarm") -Force | Out-Null

$standalone = Join-Path $app ".next\standalone"
if (!(Test-Path $standalone)) { throw "Run npm run build before packaging." }
Copy-Item -Path (Join-Path $standalone "*") -Destination (Join-Path $bundle "app") -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $bundle "app\.next") -Force | Out-Null
Copy-Item -Path (Join-Path $app ".next\static") -Destination (Join-Path $bundle "app\.next\static") -Recurse -Force
if (Test-Path (Join-Path $app "public")) { Copy-Item -Path (Join-Path $app "public") -Destination (Join-Path $bundle "app\public") -Recurse -Force }
Copy-Item -Path (Join-Path $app "README.md") -Destination (Join-Path $bundle "README.md") -Force
Copy-Item -Path (Join-Path $app "start-local.bat") -Destination (Join-Path $bundle "start-local.bat") -Force

$runtime = Join-Path $bundle "runtime\codefarm"
$include = @("control_server.py", "agent_orchestrator.py", "codefarm_common.py", "product.json", "README.md", "LICENSE", "core", "digestive-engine", "genome-bank", "immune-system", "nutrient-pool", "observatory", "organisms", "proposals", "snapshots", "tasks", "tools", "state.json")
foreach ($name in $include) {
  $src = Join-Path $repo $name
  if (Test-Path $src) { Copy-Item -Path $src -Destination $runtime -Recurse -Force }
}
foreach ($remove in @("logs", "projects", "secrets", "__pycache__", ".git", ".terraform")) {
  $target = Join-Path $runtime $remove
  if (Test-Path $target) { Remove-Item -Path $target -Recurse -Force }
}
New-Item -ItemType Directory -Path (Join-Path $runtime "projects") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $runtime "logs") -Force | Out-Null
Compress-Archive -Path (Join-Path $bundle "*") -DestinationPath $zip -Force
Write-Host "Created $zip"
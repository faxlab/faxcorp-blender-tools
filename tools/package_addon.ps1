$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$distDir = Join-Path $repoRoot "dist"
$manifestPath = Join-Path $repoRoot "blender_manifest.toml"
$manifestText = Get-Content -Raw -LiteralPath $manifestPath

if ($manifestText -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
    throw "Could not read version from blender_manifest.toml"
}

$version = $Matches[1]
$zipPath = Join-Path $distDir "faxcorp_blender_tools-$version.zip"
$tempDir = Join-Path $distDir "_package"

if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}

New-Item -ItemType Directory -Path $distDir -Force | Out-Null
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

$files = @(
    "__init__.py",
    "align_uv_islands.py",
    "axis_mesh_clipper.py",
    "blender_manifest.toml",
    "clear_custom_normals.py",
    "constants.py",
    "layout_objects.py",
    "LICENSE",
    "panels.py",
    "preferences.py",
    "README.md",
    "rename_by_collection.py",
    "rename_to_material.py",
    "set_pivot.py",
    "shortcuts.py",
    "toolbox_menu.py",
    "utils.py"
)

foreach ($file in $files) {
    Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination (Join-Path $tempDir $file)
}

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path (Join-Path $tempDir "*") -DestinationPath $zipPath -Force
Remove-Item -Recurse -Force $tempDir

Write-Host "Created $zipPath"

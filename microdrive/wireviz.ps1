# Launcher WireViz dla projektu Mercedes Microdrive.
#
# Po co: Graphviz jest zainstalowany w "C:\Program Files\Graphviz", ale NIE ma go
# w PATH systemowym. Zamiast zmieniac ustawienia systemu, doklejamy sciezke tylko
# na czas tego wywolania.
#
# Uzycie:
#   .\microdrive\wireviz.ps1 microdrive\W_czujniki_cisnienia.yml
#   .\microdrive\wireviz.ps1 microdrive\W_czujniki_cisnienia.yml -Format dhpst
#
# Formaty:  d = DXF (nasz)  h = HTML  p = PNG  s = SVG  g = GV  t = TSV (lista mat.)

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Plik,

    [string]$Format = "dhps",
    [string]$OutputDir = "rysunki",
    [string]$OutputName = ""
)

$ErrorActionPreference = "Stop"

$graphviz = "C:\Program Files\Graphviz\bin"
if (-not (Test-Path (Join-Path $graphviz "dot.exe"))) {
    throw "Nie znaleziono dot.exe w '$graphviz'. Zainstaluj: winget install Graphviz.Graphviz"
}
if ($env:PATH -notlike "*$graphviz*") { $env:PATH = "$graphviz;$env:PATH" }

$repo = Split-Path $PSScriptRoot -Parent
$szablon = Join-Path $PSScriptRoot "_szablon.yml"
$wyjscie = Join-Path $repo $OutputDir
if (-not (Test-Path $wyjscie)) { New-Item -ItemType Directory -Path $wyjscie | Out-Null }

$argumenty = @("-p", $szablon, $Plik, "-f", $Format, "-o", $wyjscie)
if ($OutputName) { $argumenty += @("-O", $OutputName) }

& wireviz @argumenty
if ($LASTEXITCODE -ne 0) { throw "WireViz zakonczyl sie bledem $LASTEXITCODE" }

Write-Host ""
Write-Host "Gotowe. Pliki w: $wyjscie"

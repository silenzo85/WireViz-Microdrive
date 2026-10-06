# Launcher WireViz dla projektu Mercedes Microdrive.
#
# Po co istnieje: Graphviz jest zainstalowany w "C:\Program Files\Graphviz", ale NIE ma
# go w PATH systemowym. Zamiast zmieniac ustawienia systemu, doklejamy sciezke tylko na
# czas tego wywolania. Launcher scala tez arkusze strefowe przez zloz.py - natywne
# `-p/--prepend` w WireViz sklada pliki JAKO TEKST i po cichu gubi powtorzone sekcje.
#
# Uzycie:
#   .\microdrive\wireviz.ps1 -Calosc                  # wszystkie strefy na jednym rysunku
#   .\microdrive\wireviz.ps1 -Strefa czujniki_bp      # jeden arkusz strefowy
#   .\microdrive\wireviz.ps1 -Plik sciezka\do.yml     # dowolny pojedynczy plik
#
# Formaty:  d = DXF (nasz)  h = HTML  p = PNG  s = SVG  g = GV  t = TSV (lista mat.)

[CmdletBinding(DefaultParameterSetName = "Strefa")]
param(
    [Parameter(ParameterSetName = "Calosc", Mandatory = $true)]
    [switch]$Calosc,

    [Parameter(ParameterSetName = "Strefa", Mandatory = $true, Position = 0)]
    [string]$Strefa,

    [Parameter(ParameterSetName = "Plik", Mandatory = $true)]
    [string]$Plik,

    [string]$Format = "dhpst"
)

$ErrorActionPreference = "Stop"

$graphviz = "C:\Program Files\Graphviz\bin"
if (-not (Test-Path (Join-Path $graphviz "dot.exe"))) {
    throw "Nie znaleziono dot.exe w '$graphviz'. Zainstaluj: winget install Graphviz.Graphviz"
}
if ($env:PATH -notlike "*$graphviz*") { $env:PATH = "$graphviz;$env:PATH" }

$repo     = Split-Path $PSScriptRoot -Parent
$szablon  = Join-Path $PSScriptRoot "_szablon.yml"
$wspolne  = Join-Path $PSScriptRoot "_wspolne.yml"
$zloz     = Join-Path $PSScriptRoot "zloz.py"
$budowa   = Join-Path $repo "build"
$rysunki  = Join-Path $repo "rysunki"
foreach ($d in @($budowa, $rysunki)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

switch ($PSCmdlet.ParameterSetName) {
    "Calosc" {
        $arkusze = Get-ChildItem (Join-Path $PSScriptRoot "strefa_*.yml") | Sort-Object Name
        if (-not $arkusze) { throw "Nie znaleziono zadnego pliku 'strefa_*.yml' w $PSScriptRoot" }
        Write-Host "Arkusze: $($arkusze.Name -join ', ')"
        $nazwa  = "INSTALACJA_calosc"
        $zrodlo = Join-Path $budowa "$nazwa.yml"
        & python $zloz -o $zrodlo $szablon $wspolne @($arkusze.FullName)
        if ($LASTEXITCODE -ne 0) { throw "Scalanie arkuszy nie powiodlo sie" }
    }
    "Strefa" {
        $arkusz = Join-Path $PSScriptRoot "strefa_$Strefa.yml"
        if (-not (Test-Path $arkusz)) { throw "Nie ma arkusza '$arkusz'" }
        $nazwa  = "STREFA_$Strefa"
        $zrodlo = Join-Path $budowa "$nazwa.yml"
        & python $zloz -o $zrodlo $szablon $wspolne $arkusz
        if ($LASTEXITCODE -ne 0) { throw "Scalanie arkusza nie powiodlo sie" }
    }
    "Plik" {
        if (-not (Test-Path $Plik)) { throw "Nie ma pliku '$Plik'" }
        $nazwa  = [System.IO.Path]::GetFileNameWithoutExtension($Plik)
        $zrodlo = $Plik
    }
}

$arg = @($zrodlo, "-f", $Format, "-o", $rysunki, "-O", $nazwa)
if ($PSCmdlet.ParameterSetName -eq "Plik") { $arg = @("-p", $szablon) + $arg }
& wireviz @arg
if ($LASTEXITCODE -ne 0) { throw "WireViz zakonczyl sie bledem $LASTEXITCODE" }

Write-Host ""
Write-Host "Gotowe: $rysunki\$nazwa.[$($Format.ToCharArray() -join '|')]"

param(
    [switch]$WithSpeech,
    [switch]$SkipInstall,
    [ValidateRange(1024, 65535)][int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv .venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv .venv
        } else {
            throw "Installeer eerst Python 3.10 of nieuwer (bij voorkeur 3.12) en start dit script opnieuw."
        }
        if ($LASTEXITCODE -ne 0) { throw "De Python-omgeving kon niet worden aangemaakt." }
    }
    & $venvPython -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
    if ($LASTEXITCODE -ne 0) { throw "Python 3.10 of nieuwer is vereist." }
    if (-not $SkipInstall) {
        & $venvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "Installeren van requirements.txt is mislukt." }
        if ($WithSpeech) {
            & $venvPython -m pip install -r requirements-speech.txt
            if ($LASTEXITCODE -ne 0) { throw "Installeren van de optionele speechpackages is mislukt." }
        }
    }
    if (-not (Test-Path -LiteralPath ".env")) {
        Copy-Item -LiteralPath ".env.example" -Destination ".env"
        Write-Host "Nieuw .env-bestand aangemaakt. Vul GEMINI_API_KEY en GEMINI_MODEL in en herstart de app."
    }
    Write-Host "Streamlit start met Gemini op http://127.0.0.1:$Port. Stop met Ctrl+C."
    Write-Host "Er worden geen AI- of spraakmodellen gedownload. Bestaande .env blijft behouden."
    & $venvPython -m streamlit run app.py --server.port $Port
    if ($LASTEXITCODE -ne 0) { throw "Streamlit is met een fout gestopt." }
} finally {
    Pop-Location
}

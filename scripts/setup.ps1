$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" 
Write-Host "        JARVIS OS - SETUP"
Write-Host "=========================================="
Write-Host ""

# --------------------------------------------------
# 1. Verificar Python
# --------------------------------------------------

Write-Host "[1/5] Verificando Python..."

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue

    if (-not $pyCommand) {
        Write-Error "Python não foi encontrado. Instale Python 3.13 ou superior."
        exit 1
    }

    $pythonExe = "py"
    $pythonArgs = @("-3.14")
}
else {
    $pythonExe = "python"
    $pythonArgs = @()
}

# Mostrar versão
if ($pythonExe -eq "py") {
    & $pythonExe @pythonArgs --version
}
else {
    & $pythonExe --version
}

Write-Host ""

# --------------------------------------------------
# 2. Criar ambiente virtual
# --------------------------------------------------

Write-Host "[2/5] Criando ambiente virtual..."

if (-not (Test-Path ".venv")) {

    if ($pythonExe -eq "py") {
        & $pythonExe @pythonArgs -m venv .venv
    }
    else {
        & $pythonExe -m venv .venv
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Não foi possível criar o ambiente virtual."
        exit 1
    }

    Write-Host "Ambiente virtual criado."
}
else {
    Write-Host "Ambiente virtual já existe."
}

$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$venvPython = [System.IO.Path]::GetFullPath($venvPython)

if (-not (Test-Path $venvPython)) {
    Write-Error "Python do ambiente virtual não foi encontrado em: $venvPython"
    exit 1
}

Write-Host ""

# --------------------------------------------------
# 3. Atualizar pip e instalar dependências
# --------------------------------------------------

Write-Host "[3/5] Instalando dependências Python..."

& $venvPython -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao atualizar o pip."
    exit 1
}

& $venvPython -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao instalar as dependências Python."
    exit 1
}

Write-Host ""

# --------------------------------------------------
# 4. Criar arquivo .env
# --------------------------------------------------

Write-Host "[4/5] Configurando ambiente..."

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env criado."
}
else {
    Write-Host ".env já existe. Mantendo configuração atual."
}

Write-Host ""

# --------------------------------------------------
# 5. Instalar dependências Node
# --------------------------------------------------

Write-Host "[5/5] Instalando dependências do Electron/React..."

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm não foi encontrado. Instale Node.js LTS."
    exit 1
}

npm install

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao instalar dependências do Node.js."
    exit 1
}

Write-Host ""
Write-Host "=========================================="
Write-Host "       JARVIS OS CONFIGURADO"
Write-Host "=========================================="
Write-Host ""
Write-Host "Python:"
& $venvPython --version

Write-Host ""
Write-Host "Próximos passos:"
Write-Host ""
Write-Host "1. Iniciar o Python Core:"
Write-Host "   .\scripts\start-core.ps1"
Write-Host ""
Write-Host "2. Em outro terminal iniciar o Desktop:"
Write-Host "   npm run dev"
Write-Host ""
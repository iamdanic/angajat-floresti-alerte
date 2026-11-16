# Iti spune chat_id-ul botului tau Telegram.
# Rulare:
#   powershell -ExecutionPolicy Bypass -File ".\ia-chat-id.ps1"

$ErrorActionPreference = 'Stop'

Write-Host "=== Afla chat_id-ul ===" -ForegroundColor Cyan
Write-Host ""

$t = (Read-Host "Lipeste TELEGRAM_BOT_TOKEN (de la BotFather)").Trim().Trim('"').Trim("'")

if (-not $t) {
    Write-Host "Lipsa token." -ForegroundColor Red
    exit 1
}

# 1. Verifica tokenul
try {
    $me = Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $t + "/getMe") -TimeoutSec 30
    Write-Host ("Token OK -> @" + $me.result.username) -ForegroundColor Green
} catch {
    Write-Host ("Token INVALID: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host "Ia-l iar de la BotFather: /mybots -> API Token -> Copy" -ForegroundColor Yellow
    exit 1
}

# 2. Cauta mesajele trimise botului
try {
    $r = Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $t + "/getUpdates?timeout=0") -TimeoutSec 30
} catch {
    Write-Host ("getUpdates a esuat: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

if (@($r.result).Count -eq 0) {
    Write-Host ""
    Write-Host "Niciun mesaj gasit pentru bot." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Fa exact asta:" -ForegroundColor Yellow
    Write-Host "  1. In Telegram, apasa pe lupa (cautare) si scrie username-ul botului tau"
    Write-Host "     (cel care se termina cu 'bot', l-ai ales la BotFather)"
    Write-Host "  2. Deschide chatul si trimite: /start"
    Write-Host "  3. Ruleaza din nou acest script"
    Write-Host ""
    Write-Host "Botul NU poate scrie primul - de asta trebuie sa-i scrii tu o data." -ForegroundColor Yellow
    exit 0
}

# 3. Afiseaza chat_id-ul
Write-Host ""
Write-Host "CHAT_ID-UL TAU:" -ForegroundColor Green
@($r.result) | ForEach-Object {
    $cid  = $_.message.chat.id
    $type = $_.message.chat.type
    $name = $_.message.chat.first_name
    if (-not $name) { $name = $_.message.chat.title }
    if (-not $name) { $name = "?" }
    Write-Host ("   " + $cid) -ForegroundColor Green -NoNewline
    Write-Host ("    (" + $type + ", " + $name + ")")
}

Write-Host ""
Write-Host "Copiaza NUMARUL si pune-l in GitHub:" -ForegroundColor Cyan
Write-Host "  Settings -> Secrets and variables -> Actions -> TELEGRAM_CHAT_ID -> Update" -ForegroundColor Cyan

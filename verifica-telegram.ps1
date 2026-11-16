# Verifica TELEGRAM_BOT_TOKEN si TELEGRAM_CHAT_ID.
# Rulare:
#   powershell -ExecutionPolicy Bypass -File ".\verifica-telegram.ps1"

$ErrorActionPreference = 'Stop'

Write-Host "=== Verificare Telegram / angajat.md Floresti ===" -ForegroundColor Cyan
Write-Host ""

$t = (Read-Host "Lipeste TELEGRAM_BOT_TOKEN (de la BotFather)").Trim().Trim('"').Trim("'")
$id = (Read-Host "Lipeste TELEGRAM_CHAT_ID").Trim().Trim('"').Trim("'")
Write-Host ""

if (-not $t) {
    Write-Host "Lipsa token." -ForegroundColor Red
    exit 1
}
if (-not $id) {
    Write-Host "Lipsa chat_id." -ForegroundColor Red
    exit 1
}

# 1. Tokenul
try {
    $me = Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $t + "/getMe") -TimeoutSec 30
    Write-Host ("[1] TOKEN OK  ->  @" + $me.result.username) -ForegroundColor Green
} catch {
    Write-Host ("[1] TOKEN INVALID: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host "    Ia-l iar de la BotFather: /mybots -> API Token -> Copy" -ForegroundColor Yellow
    exit 1
}

# 2. Ce mesaje exista pentru bot (asta iti arata si chat_id-ul corect)
try {
    $r = Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $t + "/getUpdates?timeout=0") -TimeoutSec 30
    if (@($r.result).Count -gt 0) {
        Write-Host "[2] Mesaje gasite pentru bot:" -ForegroundColor Green
        @($r.result) | ForEach-Object {
            $cid = $_.message.chat.id
            $txt = $_.message.text
            Write-Host ("     chat.id = " + $cid + "   text = " + $txt)
        }
        Write-Host "     -> compara cu valoarea lipita mai sus." -ForegroundColor Yellow
    } else {
        Write-Host "[2] Niciun mesaj in asteptare pentru bot." -ForegroundColor Yellow
        Write-Host "    Daca nu ai trimis /start botului in Telegram, fa-o si ruleaza din nou." -ForegroundColor Yellow
    }
} catch {
    Write-Host ("[2] getUpdates a esuat: " + $_.Exception.Message) -ForegroundColor Red
}

# 3. Trimite un mesaj de test
$body = @{
    chat_id = $id
    text    = "Test reusit - alertele de joburi Floresti functioneaza."
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $t + "/sendMessage") `
        -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30 | Out-Null
    Write-Host ""
    Write-Host "[3] CHAT_ID CORECT - verifica telefonul, mesajul a plecat." -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host ("[3] CHAT_ID GRESIT: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host '    Ia numarul din linia care incepe cu "chat":{"id": ...}' -ForegroundColor Yellow
    Write-Host '    ATENTIE: NU este "update_id" de la inceputul raspunsului.' -ForegroundColor Yellow
    exit 1
}

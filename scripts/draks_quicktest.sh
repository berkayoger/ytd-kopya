#!/usr/bin/env bash
set -euo pipefail

# Hızlı deneme script'i
# Kullanım:
#   ./scripts/draks_quicktest.sh http://localhost:4000
#
# Not: JWT gerekiyorsa AUTH_HEADER değişkenini doldurun.

BASE_URL="${1:-http://localhost:4000}"
AUTH_HEADER=""   # Örn: AUTH_HEADER="Authorization: Bearer <TOKEN>"

echo "==> Health kontrolü"
curl -sS "${BASE_URL}/api/draks/health" | jq .

echo
echo "==> decision/run (örnek candles ile)"
NOW="$(date +%s)"
PAYLOAD="$(cat <<JSON
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "candles": [
    { "ts": $((NOW-3600*5)), "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1200 },
    { "ts": $((NOW-3600*4)), "open": 105, "high": 111, "low": 100, "close": 108, "volume": 1300 },
    { "ts": $((NOW-3600*3)), "open": 108, "high": 115, "low": 104, "close": 113, "volume": 1400 },
    { "ts": $((NOW-3600*2)), "open": 113, "high": 116, "low": 110, "close": 114, "volume": 1500 },
    { "ts": $((NOW-3600*1)), "open": 114, "high": 118, "low": 112, "close": 117, "volume": 1600 }
  ]
}
JSON
)"
curl -sS -H "Content-Type: application/json" ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$PAYLOAD" \
  "${BASE_URL}/api/draks/decision/run" | jq .

echo
echo "==> copy/evaluate"
# Aynı candles'ı kullanarak ccxt'e ihtiyaç bırakmayalım
COPY_PAYLOAD="$(cat <<JSON
{

"symbol": "BTC/USDT",

"side": "BUY",

"size": 1000,

"timeframe": "1h",

"candles": [

{ "ts": $((NOW-3600*5)), "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1200 },

{ "ts": $((NOW-3600*4)), "open": 105, "high": 111, "low": 100, "close": 108, "volume": 1300 },

{ "ts": $((NOW-3600*3)), "open": 108, "high": 115, "low": 104, "close": 113, "volume": 1400 },

{ "ts": $((NOW-3600*2)), "open": 113, "high": 116, "low": 110, "close": 114, "volume": 1500 },

{ "ts": $((NOW-3600*1)), "open": 114, "high": 118, "low": 112, "close": 117, "volume": 1600 }

]
}
JSON
)"
curl -sS -H "Content-Type: application/json" ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -d "$COPY_PAYLOAD" \
  "${BASE_URL}/api/draks/copy/evaluate" | jq .

echo
echo "Tamam."

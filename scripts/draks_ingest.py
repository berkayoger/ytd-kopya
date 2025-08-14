"""
Basit otomatik veri çekici:
- CCXT ile kripto OHLCV (Binance varsayılan)
- yfinance ile BIST/hisse günlük
Sonuçlar ohlcv tablosuna yazar (yoksa oluşturur).
"""
from __future__ import annotations
from datetime import datetime, timezone
import time
import pandas as pd
from sqlalchemy import text, create_engine
import os

DB_URL = os.getenv("DATABASE_URL", "sqlite:///ytd.db")
ENGINE = create_engine(DB_URL, future=True)

DDL = """
CREATE TABLE IF NOT EXISTS ohlcv (
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  ts TIMESTAMP NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume REAL,
  source TEXT DEFAULT 'unknown',
  PRIMARY KEY (symbol,timeframe,ts)
);
"""
with ENGINE.begin() as con:
    con.execute(text(DDL))


def write_ohlcv(df: pd.DataFrame, *, symbol: str, timeframe: str, source: str):
    if df.empty:
        return
    df = df.copy()
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    df["source"] = source
    with ENGINE.begin() as con:
        tmp = "ohlcv_tmp"
        df.to_sql(tmp, con, if_exists="replace", index=False)
        con.execute(
            text(
                f"""
            INSERT OR IGNORE INTO ohlcv (symbol,timeframe,ts,open,high,low,close,volume,source)
            SELECT '{symbol}','{timeframe}', ts, open, high, low, close, volume, '{source}' FROM {tmp};
            DROP TABLE {tmp};
        """
            )
        )


def collect_ccxt(symbols=("BTC/USDT", "ETH/USDT"), timeframes=("1h", "1d"), limit=500, ex_id="binance"):
    import ccxt

    ex = getattr(ccxt, ex_id)({"enableRateLimit": True})
    for sym in symbols:
        for tf in timeframes:
            o = ex.fetch_ohlcv(sym, timeframe=tf, limit=limit)
            df = pd.DataFrame(o, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
            write_ohlcv(df, symbol=sym.replace(" ", ""), timeframe=tf, source=ex_id)
            time.sleep(0.25)


def collect_yf(symbols=("XU100.IS", "GARAN.IS"), interval="1d", period="720d"):
    import yfinance as yf

    for sym in symbols:
        df = yf.download(sym, interval=interval, period=period, progress=False)
        if df.empty:
            continue
        out = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        out.reset_index(inplace=True)
        out.rename(columns={out.columns[0]: "ts"}, inplace=True)
        out["ts"] = pd.to_datetime(out["ts"], utc=True)
        write_ohlcv(out[["ts", "open", "high", "low", "close", "volume"]], symbol=sym, timeframe=interval, source="yfinance")


if __name__ == "__main__":
    collect_ccxt()
    collect_yf()
    print("draks_ingest tamam")

"""
여러 매매 신호를 조합해 평가합니다. 조건 중 하나라도 충족하면 해당 사유와 함께 신호를 반환합니다.
- 골든크로스 / 데드크로스: 단기(MA_SHORT) / 장기(MA_LONG) 이동평균 교차
- RSI 과매수 / 과매도
- 전일대비 급등락 / 거래량 급증
"""
import os

from dotenv import load_dotenv

load_dotenv()

MA_SHORT = int(os.getenv("MA_SHORT", "5"))
MA_LONG = int(os.getenv("MA_LONG", "20"))
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
PRICE_CHANGE_ALERT_PCT = float(os.getenv("PRICE_CHANGE_ALERT_PCT", "3"))
VOLUME_SPIKE_MULT = float(os.getenv("VOLUME_SPIKE_MULT", "2"))


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def evaluate(name: str, ticker: str, candles: list[dict], current: dict) -> list[dict]:
    """candles: get_daily_candles() 결과(과거 종가, 오늘 미포함). current: get_current_price() 결과."""
    signals = []
    closes = [c["close"] for c in candles] + [current["price"]]
    volumes = [c["volume"] for c in candles]

    short_ma = sma(closes, MA_SHORT)
    long_ma = sma(closes, MA_LONG)
    prev_short_ma = sma(closes[:-1], MA_SHORT)
    prev_long_ma = sma(closes[:-1], MA_LONG)
    if None not in (short_ma, long_ma, prev_short_ma, prev_long_ma):
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            signals.append({
                "type": "golden_cross", "action": "buy",
                "message": f"{name}({ticker}) 골든크로스: {MA_SHORT}일선이 {MA_LONG}일선을 상향 돌파",
            })
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            signals.append({
                "type": "dead_cross", "action": "sell",
                "message": f"{name}({ticker}) 데드크로스: {MA_SHORT}일선이 {MA_LONG}일선을 하향 돌파",
            })

    r = rsi(closes, RSI_PERIOD)
    if r is not None:
        if r >= RSI_OVERBOUGHT:
            signals.append({
                "type": "rsi_overbought", "action": "sell",
                "message": f"{name}({ticker}) RSI 과매수: {r:.1f} (기준 {RSI_OVERBOUGHT})",
            })
        elif r <= RSI_OVERSOLD:
            signals.append({
                "type": "rsi_oversold", "action": "buy",
                "message": f"{name}({ticker}) RSI 과매도: {r:.1f} (기준 {RSI_OVERSOLD})",
            })

    if abs(current.get("change_rate", 0)) >= PRICE_CHANGE_ALERT_PCT:
        direction = "급등" if current["change_rate"] > 0 else "급락"
        signals.append({
            "type": "price_spike", "action": "watch",
            "message": f"{name}({ticker}) {direction}: 전일대비 {current['change_rate']:+.2f}%",
        })

    avg_vol = sma(volumes, 20)
    if avg_vol and avg_vol > 0 and current.get("volume", 0) >= avg_vol * VOLUME_SPIKE_MULT:
        signals.append({
            "type": "volume_spike", "action": "watch",
            "message": f"{name}({ticker}) 거래량 급증: 20일 평균 대비 {current['volume'] / avg_vol:.1f}배",
        })

    return signals

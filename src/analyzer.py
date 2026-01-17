"""
テクニカル分析モジュール
移動平均線を使った売買シグナルの判定を行う
"""

import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """シグナルの種類"""
    DEAD_CROSS = "dead_cross"      # デッドクロス（売りシグナル）
    GOLDEN_CROSS = "golden_cross"  # ゴールデンクロス（買いシグナル）
    HOLD = "hold"                  # 保持（シグナルなし）


@dataclass
class AnalysisResult:
    """分析結果を格納するデータクラス"""
    stock_code: str
    stock_name: str
    current_price: float
    purchase_price: float
    profit_rate: float          # 損益率（%）
    short_ma: float             # 短期移動平均
    long_ma: float              # 長期移動平均
    signal: SignalType          # シグナル
    signal_strength: str        # シグナルの強さ（strong/weak）
    
    @property
    def profit_loss(self) -> float:
        """損益額を計算"""
        return self.current_price - self.purchase_price
    
    @property
    def is_sell_signal(self) -> bool:
        """売りシグナルかどうか"""
        return self.signal == SignalType.DEAD_CROSS


def calculate_moving_average(
    df: pd.DataFrame,
    period: int,
    column: str = 'Close'
) -> pd.Series:
    """
    移動平均を計算する
    
    Args:
        df: 株価データのDataFrame
        period: 移動平均の期間
        column: 計算に使用するカラム名
    
    Returns:
        移動平均のSeries
    """
    return df[column].rolling(window=period).mean()


def detect_cross(
    short_ma: pd.Series,
    long_ma: pd.Series
) -> Optional[SignalType]:
    """
    ゴールデンクロス/デッドクロスを検出する
    
    Args:
        short_ma: 短期移動平均
        long_ma: 長期移動平均
    
    Returns:
        検出されたシグナル
    """
    if len(short_ma) < 2 or len(long_ma) < 2:
        return SignalType.HOLD
    
    # 直近2日間のデータで判定
    prev_short = short_ma.iloc[-2]
    prev_long = long_ma.iloc[-2]
    curr_short = short_ma.iloc[-1]
    curr_long = long_ma.iloc[-1]
    
    # NaN チェック
    if pd.isna(prev_short) or pd.isna(prev_long) or pd.isna(curr_short) or pd.isna(curr_long):
        return SignalType.HOLD
    
    # デッドクロス: 短期線が長期線を上から下に抜ける
    if prev_short >= prev_long and curr_short < curr_long:
        return SignalType.DEAD_CROSS
    
    # ゴールデンクロス: 短期線が長期線を下から上に抜ける
    if prev_short <= prev_long and curr_short > curr_long:
        return SignalType.GOLDEN_CROSS
    
    return SignalType.HOLD


def calculate_signal_strength(
    short_ma: float,
    long_ma: float,
    current_price: float
) -> str:
    """
    シグナルの強さを計算する
    
    Args:
        short_ma: 短期移動平均
        long_ma: 長期移動平均
        current_price: 現在の株価
    
    Returns:
        "strong" または "weak"
    """
    # 移動平均線と現在価格の乖離率で判定
    ma_diff_rate = abs(short_ma - long_ma) / long_ma * 100
    price_diff_rate = abs(current_price - short_ma) / short_ma * 100
    
    # 乖離率が1%以上なら強いシグナル
    if ma_diff_rate >= 1.0 or price_diff_rate >= 2.0:
        return "strong"
    return "weak"


def analyze_stock(
    df: pd.DataFrame,
    stock_code: str,
    stock_name: str,
    purchase_price: float,
    short_period: int = 5,
    long_period: int = 25
) -> Optional[AnalysisResult]:
    """
    株価データを分析してシグナルを判定する
    
    Args:
        df: 株価データのDataFrame
        stock_code: 銘柄コード
        stock_name: 銘柄名
        purchase_price: 購入価格
        short_period: 短期移動平均の期間
        long_period: 長期移動平均の期間
    
    Returns:
        分析結果（AnalysisResult）
    """
    if df is None or df.empty:
        return None
    
    # 移動平均を計算
    short_ma = calculate_moving_average(df, short_period)
    long_ma = calculate_moving_average(df, long_period)
    
    # 現在の値を取得
    current_price = df['Close'].iloc[-1]
    current_short_ma = short_ma.iloc[-1]
    current_long_ma = long_ma.iloc[-1]
    
    # NaN チェック
    if pd.isna(current_short_ma) or pd.isna(current_long_ma):
        print(f"警告: {stock_code} の移動平均を計算するのに十分なデータがありません")
        return None
    
    # シグナル検出
    detected_signal = detect_cross(short_ma, long_ma)
    signal = detected_signal if detected_signal is not None else SignalType.HOLD
    
    # 損益率を計算
    profit_rate = (current_price - purchase_price) / purchase_price * 100
    
    # シグナルの強さを計算
    signal_strength = calculate_signal_strength(
        current_short_ma, current_long_ma, current_price
    )
    
    return AnalysisResult(
        stock_code=stock_code,
        stock_name=stock_name,
        current_price=current_price,
        purchase_price=purchase_price,
        profit_rate=profit_rate,
        short_ma=current_short_ma,
        long_ma=current_long_ma,
        signal=signal,
        signal_strength=signal_strength
    )


def check_trend(short_ma: pd.Series, long_ma: pd.Series) -> str:
    """
    現在のトレンドを判定する
    
    Args:
        short_ma: 短期移動平均
        long_ma: 長期移動平均
    
    Returns:
        "uptrend"（上昇トレンド）, "downtrend"（下降トレンド）, "sideways"（横ばい）
    """
    curr_short = short_ma.iloc[-1]
    curr_long = long_ma.iloc[-1]
    
    if pd.isna(curr_short) or pd.isna(curr_long):
        return "unknown"
    
    diff_rate = (curr_short - curr_long) / curr_long * 100
    
    if diff_rate > 1.0:
        return "uptrend"
    elif diff_rate < -1.0:
        return "downtrend"
    else:
        return "sideways"


if __name__ == "__main__":
    # テスト実行
    from stock_fetcher import fetch_stock_data
    
    test_code = "7203.T"
    df = fetch_stock_data(test_code)
    
    if df is not None:
        result = analyze_stock(
            df=df,
            stock_code=test_code,
            stock_name="トヨタ自動車",
            purchase_price=2500
        )
        
        if result:
            print(f"\n===== {result.stock_name} ({result.stock_code}) =====")
            print(f"現在価格: {result.current_price:.2f}円")
            print(f"購入価格: {result.purchase_price:.2f}円")
            print(f"損益率: {result.profit_rate:+.2f}%")
            print(f"5日移動平均: {result.short_ma:.2f}")
            print(f"25日移動平均: {result.long_ma:.2f}")
            print(f"シグナル: {result.signal.value}")
            print(f"シグナル強度: {result.signal_strength}")

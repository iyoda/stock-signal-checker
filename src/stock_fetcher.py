"""
株価データ取得モジュール
Stooq.comを使用して日本株の株価データを取得する
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import requests
from io import StringIO


def convert_to_stooq_code(stock_code: str) -> str:
    """
    銘柄コードをStooq形式に変換する
    
    Args:
        stock_code: 銘柄コード（例: "7203.T" または "7203"）
    
    Returns:
        Stooq形式のコード（例: "7203.JP"）
    """
    # .T サフィックスを除去
    code = stock_code.replace('.T', '').replace('.t', '')
    # Stooq形式に変換（日本株は .JP）
    return f"{code}.JP"


def fetch_stock_data(
    stock_code: str,
    period_days: int = 120
) -> Optional[pd.DataFrame]:
    """
    指定した銘柄の株価データを取得する
    
    Args:
        stock_code: 銘柄コード（日本株は "7203.T" または "7203" 形式）
        period_days: 取得する日数（デフォルト60日）
    
    Returns:
        株価データのDataFrame（Open, High, Low, Close, Volume）
        取得失敗時はNone
    """
    try:
        stooq_code = convert_to_stooq_code(stock_code)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Stooq CSV API を使用
        url = (
            f"https://stooq.com/q/d/l/"
            f"?s={stooq_code}"
            f"&d1={start_date.strftime('%Y%m%d')}"
            f"&d2={end_date.strftime('%Y%m%d')}"
            f"&i=d"  # daily
        )
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # CSVデータをDataFrameに変換
        df = pd.read_csv(StringIO(response.text))
        
        if df.empty or 'Close' not in df.columns:
            print(f"警告: {stock_code} のデータが取得できませんでした")
            return None
        
        # 日付をインデックスに設定
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"エラー: {stock_code} のデータ取得中に通信エラー: {e}")
        return None
    except Exception as e:
        print(f"エラー: {stock_code} のデータ取得中にエラーが発生しました: {e}")
        return None


def get_current_price(stock_code: str) -> Optional[float]:
    """
    指定した銘柄の現在の株価を取得する
    
    Args:
        stock_code: 銘柄コード
    
    Returns:
        現在の株価（取得失敗時はNone）
    """
    df = fetch_stock_data(stock_code, period_days=10)
    
    if df is not None and not df.empty:
        return df['Close'].iloc[-1]
    
    return None


def fetch_multiple_stocks(
    stock_codes: list[str],
    period_days: int = 120
) -> dict[str, pd.DataFrame]:
    """
    複数銘柄の株価データを一括取得する
    
    Args:
        stock_codes: 銘柄コードのリスト
        period_days: 取得する日数
    
    Returns:
        銘柄コードをキー、DataFrameを値とする辞書
    """
    results = {}
    
    for code in stock_codes:
        df = fetch_stock_data(code, period_days)
        if df is not None:
            results[code] = df
    
    return results


if __name__ == "__main__":
    # テスト実行
    test_code = "7203.T"  # トヨタ自動車
    print(f"\n{test_code} の株価データを取得中...")
    
    df = fetch_stock_data(test_code)
    if df is not None:
        print(f"\n最新5日間のデータ:")
        print(df.tail())
        
        current = get_current_price(test_code)
        if current:
            print(f"\n現在の株価: {current:.2f}円")
    else:
        print("データ取得に失敗しました")

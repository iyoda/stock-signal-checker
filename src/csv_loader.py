#!/usr/bin/env python3
"""
CSV Loader - マネックス証券のCSVファイルからポートフォリオを読み込む
"""

import csv
from pathlib import Path
from typing import Optional

# デフォルトの移動平均線設定（週1回チェック向け）
DEFAULT_SHORT_PERIOD = 25   # 短期: 約1ヶ月（25営業日）
DEFAULT_LONG_PERIOD = 75    # 長期: 約3ヶ月（75営業日）

# CSVファイルのパターン
CSV_PATTERN = "stockposition_*.csv"


def find_latest_csv(data_dir: Path) -> Optional[Path]:
    """
    data/ ディレクトリ内の最新のCSVファイルを検索する
    
    ファイル名のタイムスタンプ（stockposition_YYYYMMDDHHmmss.csv）で
    最新のものを判定する
    
    Args:
        data_dir: 検索対象のディレクトリ
    
    Returns:
        最新のCSVファイルのパス、見つからない場合はNone
    """
    if not data_dir.exists():
        return None
    
    csv_files = list(data_dir.glob(CSV_PATTERN))
    
    if not csv_files:
        return None
    
    # ファイル名でソート（タイムスタンプが含まれているので降順で最新が先頭）
    csv_files.sort(reverse=True)
    
    return csv_files[0]


def load_portfolio_from_csv(
    csv_path: Path,
    short_period: int = DEFAULT_SHORT_PERIOD,
    long_period: int = DEFAULT_LONG_PERIOD
) -> dict:
    """
    マネックス証券のCSVファイルからポートフォリオを読み込む
    
    CSVファイルはShift-JIS エンコーディングで保存されている
    
    Args:
        csv_path: CSVファイルのパス
        short_period: 短期移動平均の日数
        long_period: 長期移動平均の日数
    
    Returns:
        portfolio.yaml と同じ形式の辞書
    
    Raises:
        FileNotFoundError: CSVファイルが見つからない場合
        ValueError: CSVの形式が不正な場合
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    
    stocks = []
    
    with open(csv_path, 'r', encoding='shift_jis') as f:
        reader = csv.DictReader(f)
        
        # 必要な列が存在するか確認
        required_columns = ['銘柄コード', '銘柄名', '平均取得単価', '保有数']
        if reader.fieldnames is None:
            raise ValueError("CSVファイルにヘッダーがありません")
        
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            raise ValueError(f"必要な列が見つかりません: {missing_columns}")
        
        for row in reader:
            # 銘柄コードに .T を付加（日本株）
            code = row['銘柄コード'].strip()
            if not code.endswith('.T'):
                code = f"{code}.T"
            
            # 銘柄名
            name = row['銘柄名'].strip()
            
            # 平均取得単価（小数点以下も含む）
            try:
                purchase_price = float(row['平均取得単価'])
            except ValueError:
                print(f"警告: {name} の取得単価が不正です: {row['平均取得単価']}")
                continue
            
            # 保有数
            try:
                quantity = int(row['保有数'])
            except ValueError:
                print(f"警告: {name} の保有数が不正です: {row['保有数']}")
                continue
            
            # 保有数が0以下の場合はスキップ
            if quantity <= 0:
                continue
            
            stocks.append({
                'code': code,
                'name': name,
                'purchase_price': purchase_price,
                'quantity': quantity
            })
    
    if not stocks:
        raise ValueError("CSVファイルに有効な銘柄データがありません")
    
    return {
        'settings': {
            'short_period': short_period,
            'long_period': long_period
        },
        'stocks': stocks
    }


def get_csv_info(csv_path: Path) -> dict:
    """
    CSVファイルの情報を取得する（デバッグ・表示用）
    
    Args:
        csv_path: CSVファイルのパス
    
    Returns:
        ファイル情報の辞書
    """
    from datetime import datetime
    
    stat = csv_path.stat()
    
    # ファイル名からタイムスタンプを抽出
    filename = csv_path.stem  # stockposition_YYYYMMDDHHmmss
    timestamp_str = filename.replace('stockposition_', '')
    
    try:
        file_timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
        timestamp_display = file_timestamp.strftime('%Y年%m月%d日 %H:%M:%S')
    except ValueError:
        timestamp_display = "不明"
    
    return {
        'path': str(csv_path),
        'filename': csv_path.name,
        'size': stat.st_size,
        'timestamp': timestamp_display
    }

#!/usr/bin/env python3
"""
Stock Signal Checker - メインエントリーポイント
保有株式の売却タイミングを移動平均線で分析し、Slackに通知する
"""

import os
import sys
import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv

from stock_fetcher import fetch_stock_data
from analyzer import analyze_stock, AnalysisResult, SignalType
from notifier import notify_results, create_summary_message
from csv_loader import find_latest_csv, load_portfolio_from_csv, get_csv_info


def load_portfolio(config_path: str) -> dict:
    """
    ポートフォリオ設定ファイルを読み込む
    
    Args:
        config_path: 設定ファイルのパス
    
    Returns:
        設定情報の辞書
    """
    path = Path(config_path)
    
    if not path.exists():
        print(f"エラー: 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_signals(
    portfolio: dict,
    verbose: bool = False
) -> list[AnalysisResult]:
    """
    ポートフォリオ内の全銘柄をチェックする
    
    Args:
        portfolio: ポートフォリオ設定
        verbose: 詳細出力モード
    
    Returns:
        分析結果のリスト
    """
    settings = portfolio.get('settings', {})
    short_period = settings.get('short_period', 5)
    long_period = settings.get('long_period', 25)
    
    stocks = portfolio.get('stocks', [])
    
    if not stocks:
        print("警告: チェック対象の銘柄がありません")
        return []
    
    results = []
    
    print(f"\n{len(stocks)}銘柄をチェック中...")
    print(f"移動平均線設定: 短期={short_period}日, 長期={long_period}日\n")
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        purchase_price = stock['purchase_price']
        
        if verbose:
            print(f"  チェック中: {name} ({code})...")
        
        # 株価データ取得
        # 営業日ベースの移動平均を計算するため、カレンダー日数で約1.5倍のデータが必要
        period_days = int(long_period * 1.5) + 30
        df = fetch_stock_data(code, period_days=period_days)
        
        if df is None:
            print(f"  警告: {name} ({code}) のデータを取得できませんでした")
            continue
        
        # 分析実行
        result = analyze_stock(
            df=df,
            stock_code=code,
            stock_name=name,
            purchase_price=purchase_price,
            short_period=short_period,
            long_period=long_period
        )
        
        if result:
            results.append(result)
            if verbose:
                signal_mark = ""
                if result.signal == SignalType.DEAD_CROSS:
                    signal_mark = " [売りシグナル]"
                elif result.signal == SignalType.GOLDEN_CROSS:
                    signal_mark = " [買いシグナル]"
                print(f"    -> {result.current_price:,.0f}円 ({result.profit_rate:+.2f}%){signal_mark}")
    
    return results


def print_results(results: list[AnalysisResult]) -> None:
    """
    分析結果をコンソールに表示する
    """
    print("\n" + "=" * 60)
    print(create_summary_message(results))
    print("=" * 60)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='保有株式の売却タイミングをチェックする'
    )
    parser.add_argument(
        '-c', '--config',
        default='config/portfolio.yaml',
        help='ポートフォリオ設定ファイルのパス（デフォルト: config/portfolio.yaml）'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='詳細出力モード'
    )
    parser.add_argument(
        '--no-slack',
        action='store_true',
        help='Slack通知を無効にする'
    )
    parser.add_argument(
        '--sell-only',
        action='store_true',
        help='売りシグナルがある場合のみSlack通知'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Slack通知せずに結果を表示のみ'
    )
    parser.add_argument(
        '--use-csv',
        action='store_true',
        help='data/ ディレクトリから最新のCSVファイルを使用'
    )
    parser.add_argument(
        '--csv',
        type=str,
        metavar='PATH',
        help='使用するCSVファイルのパスを指定'
    )
    
    args = parser.parse_args()
    
    # 環境変数の読み込み
    load_dotenv()
    
    # スクリプトのディレクトリを基準にパスを解決
    script_dir = Path(__file__).parent.parent
    config_path = script_dir / args.config
    data_dir = script_dir / 'data'
    
    print("=" * 60)
    print("Stock Signal Checker")
    print("=" * 60)
    
    # ポートフォリオ読み込み
    portfolio = None
    
    # CSVファイルからの読み込み
    if args.csv:
        # --csv オプションで直接指定
        csv_path = Path(args.csv)
        if not csv_path.is_absolute():
            csv_path = script_dir / csv_path
        
        try:
            csv_info = get_csv_info(csv_path)
            print(f"\nCSVファイル: {csv_info['filename']}")
            print(f"データ取得日時: {csv_info['timestamp']}")
            portfolio = load_portfolio_from_csv(csv_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"エラー: {e}")
            sys.exit(1)
    
    elif args.use_csv:
        # --use-csv オプションで data/ から自動検索
        csv_path = find_latest_csv(data_dir)
        
        if csv_path is None:
            print(f"エラー: {data_dir} にCSVファイルが見つかりません")
            print("マネックス証券からダウンロードしたCSVファイルを data/ ディレクトリに配置してください")
            sys.exit(1)
        
        try:
            csv_info = get_csv_info(csv_path)
            print(f"\nCSVファイル: {csv_info['filename']}")
            print(f"データ取得日時: {csv_info['timestamp']}")
            portfolio = load_portfolio_from_csv(csv_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"エラー: {e}")
            sys.exit(1)
    
    else:
        # 従来通り YAML ファイルから読み込み
        portfolio = load_portfolio(str(config_path))
    
    # シグナルチェック
    results = check_signals(portfolio, verbose=args.verbose)
    
    if not results:
        print("\n分析結果がありません")
        return
    
    # 結果を表示
    print_results(results)
    
    # Slack通知
    if args.dry_run or args.no_slack:
        print("\n(Slack通知はスキップされました)")
    else:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if webhook_url:
            print("\nSlackに通知中...")
            success = notify_results(
                results,
                webhook_url=webhook_url,
                sell_signals_only=args.sell_only
            )
            if success:
                print("Slack通知が完了しました")
            else:
                print("Slack通知に失敗しました")
        else:
            print("\n警告: SLACK_WEBHOOK_URL が設定されていないため、Slack通知をスキップします")
            print("Slack通知を有効にするには、.env ファイルに SLACK_WEBHOOK_URL を設定してください")


if __name__ == "__main__":
    main()

"""
Slack通知モジュール
分析結果をSlackに通知する
"""

import os
import requests
from typing import Optional
from datetime import datetime

from analyzer import AnalysisResult, SignalType, EnhancedSignalType


def send_slack_notification(
    webhook_url: str,
    message: str
) -> bool:
    """
    Slackにメッセージを送信する
    
    Args:
        webhook_url: Slack Webhook URL
        message: 送信するメッセージ
    
    Returns:
        送信成功時True、失敗時False
    """
    try:
        payload = {"text": message}
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"Slack通知エラー: ステータスコード {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Slack通知エラー: {e}")
        return False


def format_signal_emoji(signal: SignalType) -> str:
    """シグナルに対応する絵文字を返す"""
    if signal == SignalType.DEAD_CROSS:
        return ":chart_with_downwards_trend:"  # 売りシグナル
    elif signal == SignalType.GOLDEN_CROSS:
        return ":chart_with_upwards_trend:"    # 買いシグナル
    else:
        return ":heavy_minus_sign:"            # 保持


def format_enhanced_signal_label(enhanced_signal: EnhancedSignalType) -> str:
    """強化シグナルの表示ラベルを返す"""
    labels = {
        EnhancedSignalType.PROFIT_TAKING: "利益確定推奨",
        EnhancedSignalType.CONSIDER_SELL: "売却検討",
        EnhancedSignalType.STOP_LOSS: "損切り検討",
        EnhancedSignalType.RECOVERY_SIGN: "回復兆候",
        EnhancedSignalType.UPTREND_CONTINUE: "上昇継続",
        EnhancedSignalType.WATCH_CLOSELY: "要注意",
        EnhancedSignalType.CONSIDER_PROFIT: "利益確定検討",
        EnhancedSignalType.HOLD: "",
    }
    return labels.get(enhanced_signal, "")


def format_result_message(result: AnalysisResult) -> str:
    """
    分析結果を読みやすいメッセージにフォーマットする
    
    Args:
        result: 分析結果
    
    Returns:
        フォーマットされたメッセージ
    """
    emoji = format_signal_emoji(result.signal)
    profit_emoji = ":arrow_up:" if result.profit_rate >= 0 else ":arrow_down:"
    
    signal_text = {
        SignalType.DEAD_CROSS: "デッドクロス（売りシグナル）",
        SignalType.GOLDEN_CROSS: "ゴールデンクロス（買いシグナル）",
        SignalType.HOLD: "シグナルなし"
    }
    
    lines = [
        f"{emoji} *{result.stock_name}* ({result.stock_code})",
        f"",
        f"現在価格: {result.current_price:,.0f}円",
        f"購入価格: {result.purchase_price:,.0f}円",
        f"損益率: {profit_emoji} {result.profit_rate:+.2f}%",
        f"",
        f"短期MA: {result.short_ma:,.0f}円",
        f"長期MA: {result.long_ma:,.0f}円",
        f"",
        f"*シグナル*: {signal_text[result.signal]}",
        f"シグナル強度: {result.signal_strength}"
    ]
    
    return "\n".join(lines)


def create_summary_message(
    results: list[AnalysisResult],
    sell_signals_only: bool = False
) -> str:
    """
    複数の分析結果をまとめたメッセージを作成する
    
    Args:
        results: 分析結果のリスト
        sell_signals_only: Trueの場合、売りシグナルのみを含める
    
    Returns:
        フォーマットされたサマリーメッセージ
    """
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    # フィルタリング
    if sell_signals_only:
        filtered = [r for r in results if r.is_sell_signal]
    else:
        filtered = results
    
    # ヘッダー
    lines = [
        f":bell: *株式シグナルチェック結果*",
        f"実行日時: {now}",
        f"チェック銘柄数: {len(filtered)}",
        ""
    ]
    
    # アクション推奨（売却系シグナル）
    action_recommended = [r for r in filtered if r.is_action_recommended]
    if action_recommended:
        lines.append(":rotating_light: *アクション推奨*")
        for r in action_recommended:
            label = format_enhanced_signal_label(r.enhanced_signal)
            lines.append(f"  • {r.stock_name}: {r.current_price:,.0f}円 ({r.profit_rate:+.2f}%)")
            lines.append(f"    【{label}】{r.action_message}")
        lines.append("")
    
    # 買いシグナル（回復兆候・上昇継続）
    buy_signals = [r for r in filtered if r.signal == SignalType.GOLDEN_CROSS]
    if buy_signals:
        lines.append(":star: *買いシグナル検出*")
        for r in buy_signals:
            label = format_enhanced_signal_label(r.enhanced_signal)
            lines.append(f"  • {r.stock_name}: {r.current_price:,.0f}円 ({r.profit_rate:+.2f}%)")
            if label:
                lines.append(f"    【{label}】{r.action_message}")
        lines.append("")
    
    # 要注意（シグナルなしだが損益率で警告）
    watch_closely = [r for r in filtered if r.is_watch_signal]
    if watch_closely and not sell_signals_only:
        lines.append(":warning: *要注意*")
        for r in watch_closely:
            label = format_enhanced_signal_label(r.enhanced_signal)
            lines.append(f"  • {r.stock_name}: {r.current_price:,.0f}円 ({r.profit_rate:+.2f}%)")
            lines.append(f"    【{label}】{r.action_message}")
        lines.append("")
    
    # シグナルなし（通常保持）
    no_signals = [r for r in filtered if r.enhanced_signal == EnhancedSignalType.HOLD]
    if no_signals and not sell_signals_only:
        lines.append(":heavy_minus_sign: *シグナルなし*")
        for r in no_signals:
            lines.append(f"  • {r.stock_name}: {r.current_price:,.0f}円 ({r.profit_rate:+.2f}%)")
        lines.append("")
    
    # サマリー
    if not action_recommended and not buy_signals and not watch_closely:
        lines.append(":white_check_mark: 現在、注目すべきシグナルはありません")
    
    return "\n".join(lines)


def notify_results(
    results: list[AnalysisResult],
    webhook_url: Optional[str] = None,
    sell_signals_only: bool = False
) -> bool:
    """
    分析結果をSlackに通知する
    
    Args:
        results: 分析結果のリスト
        webhook_url: Slack Webhook URL（Noneの場合は環境変数から取得）
        sell_signals_only: Trueの場合、売りシグナルがある時のみ通知
    
    Returns:
        送信成功時True
    """
    if webhook_url is None:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        print("エラー: Slack Webhook URLが設定されていません")
        print("環境変数 SLACK_WEBHOOK_URL を設定するか、引数で指定してください")
        return False
    
    # 売りシグナルのみモードで、シグナルがない場合は通知しない
    if sell_signals_only:
        has_sell = any(r.is_sell_signal for r in results)
        if not has_sell:
            print("売りシグナルなし。通知をスキップします。")
            return True
    
    message = create_summary_message(results, sell_signals_only)
    return send_slack_notification(webhook_url, message)


if __name__ == "__main__":
    # テスト用のダミーデータ
    test_results = [
        AnalysisResult(
            stock_code="7203.T",
            stock_name="トヨタ自動車",
            current_price=2800,
            purchase_price=2500,
            profit_rate=12.0,
            short_ma=2750,
            long_ma=2800,
            signal=SignalType.DEAD_CROSS,
            signal_strength="strong"
        ),
        AnalysisResult(
            stock_code="9984.T",
            stock_name="ソフトバンクグループ",
            current_price=6500,
            purchase_price=6000,
            profit_rate=8.33,
            short_ma=6400,
            long_ma=6300,
            signal=SignalType.HOLD,
            signal_strength="weak"
        )
    ]
    
    # コンソールに出力（テスト用）
    print(create_summary_message(test_results))

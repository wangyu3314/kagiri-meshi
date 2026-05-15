"""
回転寿司チェーン 期間限定メニュー RSS自動取得スクリプト
情報源: Google ニュース RSS

使い方:
  pip install feedparser schedule
  python rss_fetcher.py
"""

import feedparser
import json
import os
import hashlib
import schedule
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# =====================
# 監視するRSSフィード一覧
# Google ニュースの検索RSSを使用（無料・制限なし）
# =====================
FEEDS = [
    # ── 回転寿司 ──
    {
        "shop": "スシロー",
        "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%B7%E3%83%AD%E3%83%BC%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja",
        "category": "sushi",
    },
    {
        "shop": "はま寿司",
        "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%BE%E5%AF%BF%E5%8F%B8%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja",
        "category": "sushi",
    },
    {
        "shop": "くら寿司",
        "url": "https://news.google.com/rss/search?q=%E3%81%8F%E3%82%89%E5%AF%BF%E5%8F%B8%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja",
        "category": "sushi",
    },
    {
        "shop": "かっぱ寿司",
        "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A3%E3%81%B1%E5%AF%BF%E5%8F%B8%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja",
        "category": "sushi",
    },

    # ── 新しいジャンルを追加するときはここに追記するだけ ──
    # 使えるカテゴリ: sushi / burger / cafe / fastfood / convenience / family / ramen / sweets
    #
    # 例:
    # {
    #     "shop": "マクドナルド",
    #     "url": "https://news.google.com/rss/search?q=マクドナルド+期間限定&hl=ja&gl=JP&ceid=JP:ja",
    #     "category": "burger",
    # },
]

# =====================
# フィルター設定
# =====================

# 期間限定と判断するキーワード（タイトルか本文に1つでも含まれていれば対象）
LIMITED_KEYWORDS = [
    "期間限定", "数量限定", "季節限定", "〜まで", "まで販売",
    "新発売", "復刻", "フェア", "祭り", "limited", "seasonal",
    "登場", "販売開始", "新メニュー", "新商品",
]

# 除外キーワード（1つでも含まれていれば除外）
EXCLUDE_KEYWORDS = [
    # 比較・まとめ系
    "比較", "ランキング", "まとめ", "違い", "どっちが", "おすすめ",
    "ベスト", "人気メニュー", "全メニュー", "メニュー一覧",
    # 感想・レビュー系
    "食べてみた", "食べた感想", "実食", "レビュー", "口コミ",
    "行ってみた", "試してみた", "感想", "体験",
    # ビジネス・企業情報系
    "株価", "決算", "業績", "売上", "採用", "求人", "店舗数",
    "値上げ", "閉店", "倒産",
    # その他ノイズ
    "カロリー", "糖質", "ダイエット", "レシピ", "作り方",
    "クーポンまとめ", "割引まとめ",
]

# 記事の有効期限（日数）。これより古い記事は除外する
ARTICLE_MAX_AGE_DAYS = 30

# データ保存先
DATA_FILE = "limited_menus.json"


# =====================
# ユーティリティ
# =====================

def load_data():
    """保存済みデータを読み込む"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_data(items):
    """データをJSONファイルに保存する"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {DATA_FILE} に保存しました（{len(items)}件）")


def make_id(shop, title):
    """重複チェック用のIDを生成する"""
    return hashlib.md5(f"{shop}:{title}".encode()).hexdigest()


def is_valid_article(title, summary, published_str):
    """
    掲載すべき記事かどうかを判定する。
    - 除外キーワードが含まれていたら False
    - 期間限定キーワードが含まれていなければ False
    - 公開日が ARTICLE_MAX_AGE_DAYS 日より古ければ False
    """
    text = title + " " + summary

    # 除外キーワードチェック
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False

    # 期間限定キーワードチェック
    if not any(kw in text for kw in LIMITED_KEYWORDS):
        return False

    # 公開日チェック
    if published_str:
        try:
            pub_dt = parsedate_to_datetime(published_str)
            # タイムゾーン対応
            now = datetime.now(timezone.utc)
            age = now - pub_dt.astimezone(timezone.utc)
            if age.days > ARTICLE_MAX_AGE_DAYS:
                return False
        except Exception:
            pass  # 日付パース失敗時はスキップせず通す

    return True


def purge_old_items(items):
    """
    保存済みデータから期限切れ記事を削除して返す。
    毎回のフェッチ時に呼び出すことで古いデータが溜まり続けるのを防ぐ。
    """
    now = datetime.now(timezone.utc)
    result = []
    removed = 0
    for item in items:
        pub = item.get("published", "")
        if pub:
            try:
                pub_dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
                if (now - pub_dt).days > ARTICLE_MAX_AGE_DAYS:
                    removed += 1
                    continue
            except Exception:
                pass
        result.append(item)
    if removed:
        print(f"  期限切れ {removed} 件を削除しました")
    return result


# =====================
# フェッチ処理
# =====================

def fetch_feed(feed_config):
    """1つのRSSフィードを取得してフィルタする"""
    shop = feed_config["shop"]
    url = feed_config["url"]
    category = feed_config["category"]
    new_items = []

    try:
        print(f"  取得中: {shop}")
        parsed = feedparser.parse(url)

        for entry in parsed.entries:
            title     = entry.get("title", "")
            summary   = entry.get("summary", "")
            link      = entry.get("link", "")
            published = entry.get("published", "")

            if not is_valid_article(title, summary, published):
                continue

            new_items.append({
                "id":         make_id(shop, title),
                "shop":       shop,
                "name":       title,
                "summary":    summary[:120],
                "link":       link,
                "category":   category,
                "published":  published,
                "fetched_at": datetime.now().isoformat(),
            })

    except Exception as e:
        print(f"  エラー ({shop}): {e}")

    return new_items


def run_fetch():
    """全フィードを取得して新着のみ保存する"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] フェッチ開始")

    # 既存データを読み込み、期限切れを先に削除
    existing = purge_old_items(load_data())
    existing_ids = {item["id"] for item in existing}

    all_new = []
    for feed in FEEDS:
        items    = fetch_feed(feed)
        new_only = [i for i in items if i["id"] not in existing_ids]
        all_new.extend(new_only)
        if new_only:
            print(f"  → {feed['shop']}: {len(new_only)}件の新着")

    merged = existing + all_new
    save_data(merged)

    if all_new:
        print(f"合計 {len(all_new)} 件の新着を追加しました")
    else:
        print("新着はありませんでした")


# =====================
# 起動設定
# =====================
if __name__ == "__main__":
    import sys

    print("RSS自動取得スクリプト起動")
    print(f"除外キーワード: {len(EXCLUDE_KEYWORDS)}個  有効期限: {ARTICLE_MAX_AGE_DAYS}日\n")

    # --once オプション: 1回だけ実行して終了（GitHub Actions用）
    if "--once" in sys.argv:
        run_fetch()
    else:
        # 通常モード: 毎朝8時に繰り返し実行
        print("毎朝 8:00 に自動実行します（Ctrl+C で停止）\n")
        run_fetch()
        schedule.every().day.at("08:00").do(run_fetch)
        while True:
            schedule.run_pending()
            time.sleep(60)

"""
飲食チェーン 期間限定メニュー RSS自動取得スクリプト
情報源: Google ニュース RSS

使い方:
  pip install feedparser schedule google-genai
  python rss_fetcher.py
"""

import feedparser
import json
import os
import hashlib
import schedule
import time
from google import genai
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# =====================
# 監視するRSSフィード一覧
# =====================
FEEDS = [
    # ── 回転寿司 ──
    {"shop": "スシロー", "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%B7%E3%83%AD%E3%83%BC%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "スシロー", "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%B7%E3%83%AD%E3%83%BC%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "スシロー", "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%B7%E3%83%AD%E3%83%BC%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "はま寿司", "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%BE%E5%AF%BF%E5%8F%B8%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "はま寿司", "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%BE%E5%AF%BF%E5%8F%B8%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "はま寿司", "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%BE%E5%AF%BF%E5%8F%B8%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "くら寿司", "url": "https://news.google.com/rss/search?q=%E3%81%8F%E3%82%89%E5%AF%BF%E5%8F%B8%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "くら寿司", "url": "https://news.google.com/rss/search?q=%E3%81%8F%E3%82%89%E5%AF%BF%E5%8F%B8%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "くら寿司", "url": "https://news.google.com/rss/search?q=%E3%81%8F%E3%82%89%E5%AF%BF%E5%8F%B8%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "かっぱ寿司", "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A3%E3%81%B1%E5%AF%BF%E5%8F%B8%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "かっぱ寿司", "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A3%E3%81%B1%E5%AF%BF%E5%8F%B8%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "かっぱ寿司", "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A3%E3%81%B1%E5%AF%BF%E5%8F%B8%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "魚べい", "url": "https://news.google.com/rss/search?q=%E9%AD%9A%E3%81%B9%E3%81%84%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "魚べい", "url": "https://news.google.com/rss/search?q=%E9%AD%9A%E3%81%B9%E3%81%84%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    {"shop": "魚べい", "url": "https://news.google.com/rss/search?q=%E9%AD%9A%E3%81%B9%E3%81%84%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "sushi"},
    # ── バーガー ──
    {"shop": "マクドナルド", "url": "https://news.google.com/rss/search?q=%E3%83%9E%E3%82%AF%E3%83%89%E3%83%8A%E3%83%AB%E3%83%89%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "マクドナルド", "url": "https://news.google.com/rss/search?q=%E3%83%9E%E3%82%AF%E3%83%89%E3%83%8A%E3%83%AB%E3%83%89%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "マクドナルド", "url": "https://news.google.com/rss/search?q=%E3%83%9E%E3%82%AF%E3%83%89%E3%83%8A%E3%83%AB%E3%83%89%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "モスバーガー", "url": "https://news.google.com/rss/search?q=%E3%83%A2%E3%82%B9%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "モスバーガー", "url": "https://news.google.com/rss/search?q=%E3%83%A2%E3%82%B9%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "モスバーガー", "url": "https://news.google.com/rss/search?q=%E3%83%A2%E3%82%B9%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "バーガーキング", "url": "https://news.google.com/rss/search?q=%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%E3%82%AD%E3%83%B3%E3%82%B0%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "バーガーキング", "url": "https://news.google.com/rss/search?q=%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%E3%82%AD%E3%83%B3%E3%82%B0%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "バーガーキング", "url": "https://news.google.com/rss/search?q=%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%E3%82%AD%E3%83%B3%E3%82%B0%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "フレッシュネスバーガー", "url": "https://news.google.com/rss/search?q=%E3%83%95%E3%83%AC%E3%83%83%E3%82%B7%E3%83%A5%E3%83%8D%E3%82%B9%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "フレッシュネスバーガー", "url": "https://news.google.com/rss/search?q=%E3%83%95%E3%83%AC%E3%83%83%E3%82%B7%E3%83%A5%E3%83%8D%E3%82%B9%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "フレッシュネスバーガー", "url": "https://news.google.com/rss/search?q=%E3%83%95%E3%83%AC%E3%83%83%E3%82%B7%E3%83%A5%E3%83%8D%E3%82%B9%E3%83%90%E3%83%BC%E3%82%AC%E3%83%BC%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "ゼッテリア", "url": "https://news.google.com/rss/search?q=%E3%82%BC%E3%83%83%E3%83%86%E3%83%AA%E3%82%A2%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "ゼッテリア", "url": "https://news.google.com/rss/search?q=%E3%82%BC%E3%83%83%E3%83%86%E3%83%AA%E3%82%A2%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "ゼッテリア", "url": "https://news.google.com/rss/search?q=%E3%82%BC%E3%83%83%E3%83%86%E3%83%AA%E3%82%A2%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "ケンタッキーフライドチキン", "url": "https://news.google.com/rss/search?q=%E3%82%B1%E3%83%B3%E3%82%BF%E3%83%83%E3%82%AD%E3%83%BC%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "ケンタッキーフライドチキン", "url": "https://news.google.com/rss/search?q=%E3%82%B1%E3%83%B3%E3%82%BF%E3%83%83%E3%82%AD%E3%83%BC%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    {"shop": "ケンタッキーフライドチキン", "url": "https://news.google.com/rss/search?q=%E3%82%B1%E3%83%B3%E3%82%BF%E3%83%83%E3%82%AD%E3%83%BC%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "burger"},
    # ── カフェ ──
    {"shop": "スターバックス", "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%90%E3%83%83%E3%82%AF%E3%82%B9%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "スターバックス", "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%90%E3%83%83%E3%82%AF%E3%82%B9%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "スターバックス", "url": "https://news.google.com/rss/search?q=%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%90%E3%83%83%E3%82%AF%E3%82%B9%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "ドトールコーヒー", "url": "https://news.google.com/rss/search?q=%E3%83%89%E3%83%88%E3%83%BC%E3%83%AB%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "ドトールコーヒー", "url": "https://news.google.com/rss/search?q=%E3%83%89%E3%83%88%E3%83%BC%E3%83%AB%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "ドトールコーヒー", "url": "https://news.google.com/rss/search?q=%E3%83%89%E3%83%88%E3%83%BC%E3%83%AB%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "タリーズコーヒー", "url": "https://news.google.com/rss/search?q=%E3%82%BF%E3%83%AA%E3%83%BC%E3%82%BA%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "タリーズコーヒー", "url": "https://news.google.com/rss/search?q=%E3%82%BF%E3%83%AA%E3%83%BC%E3%82%BA%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "タリーズコーヒー", "url": "https://news.google.com/rss/search?q=%E3%82%BF%E3%83%AA%E3%83%BC%E3%82%BA%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "サンマルクカフェ", "url": "https://news.google.com/rss/search?q=%E3%82%B5%E3%83%B3%E3%83%9E%E3%83%AB%E3%82%AF%E3%82%AB%E3%83%95%E3%82%A7%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "サンマルクカフェ", "url": "https://news.google.com/rss/search?q=%E3%82%B5%E3%83%B3%E3%83%9E%E3%83%AB%E3%82%AF%E3%82%AB%E3%83%95%E3%82%A7%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "サンマルクカフェ", "url": "https://news.google.com/rss/search?q=%E3%82%B5%E3%83%B3%E3%83%9E%E3%83%AB%E3%82%AF%E3%82%AB%E3%83%95%E3%82%A7%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "ミスタードーナツ", "url": "https://news.google.com/rss/search?q=%E3%83%9F%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%89%E3%83%BC%E3%83%8A%E3%83%84%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "ミスタードーナツ", "url": "https://news.google.com/rss/search?q=%E3%83%9F%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%89%E3%83%BC%E3%83%8A%E3%83%84%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "ミスタードーナツ", "url": "https://news.google.com/rss/search?q=%E3%83%9F%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%89%E3%83%BC%E3%83%8A%E3%83%84%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "コメダ珈琲店", "url": "https://news.google.com/rss/search?q=%E3%82%B3%E3%83%A1%E3%83%80%E7%8F%88%E7%90%B2%E5%BA%97%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "コメダ珈琲店", "url": "https://news.google.com/rss/search?q=%E3%82%B3%E3%83%A1%E3%83%80%E7%8F%88%E7%90%B2%E5%BA%97%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    {"shop": "コメダ珈琲店", "url": "https://news.google.com/rss/search?q=%E3%82%B3%E3%83%A1%E3%83%80%E7%8F%88%E7%90%B2%E5%BA%97%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "cafe"},
    # ── 丼 ──
    {"shop": "すき家", "url": "https://news.google.com/rss/search?q=%E3%81%99%E3%81%8D%E5%AE%B6%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "すき家", "url": "https://news.google.com/rss/search?q=%E3%81%99%E3%81%8D%E5%AE%B6%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "すき家", "url": "https://news.google.com/rss/search?q=%E3%81%99%E3%81%8D%E5%AE%B6%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "松屋", "url": "https://news.google.com/rss/search?q=%E6%9D%BE%E5%B1%8B%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "松屋", "url": "https://news.google.com/rss/search?q=%E6%9D%BE%E5%B1%8B%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "松屋", "url": "https://news.google.com/rss/search?q=%E6%9D%BE%E5%B1%8B%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "吉野家", "url": "https://news.google.com/rss/search?q=%E5%90%89%E9%87%8E%E5%AE%B6%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "吉野家", "url": "https://news.google.com/rss/search?q=%E5%90%89%E9%87%8E%E5%AE%B6%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "吉野家", "url": "https://news.google.com/rss/search?q=%E5%90%89%E9%87%8E%E5%AE%B6%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "なか卯", "url": "https://news.google.com/rss/search?q=%E3%81%AA%E3%81%8B%E5%8D%AF%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "なか卯", "url": "https://news.google.com/rss/search?q=%E3%81%AA%E3%81%8B%E5%8D%AF%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "なか卯", "url": "https://news.google.com/rss/search?q=%E3%81%AA%E3%81%8B%E5%8D%AF%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "かつや", "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A4%E3%82%84%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "かつや", "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A4%E3%82%84%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "かつや", "url": "https://news.google.com/rss/search?q=%E3%81%8B%E3%81%A4%E3%82%84%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "天丼てんや", "url": "https://news.google.com/rss/search?q=%E5%A4%A9%E4%B8%BC%E3%81%A6%E3%82%93%E3%82%84%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "天丼てんや", "url": "https://news.google.com/rss/search?q=%E5%A4%A9%E4%B8%BC%E3%81%A6%E3%82%93%E3%82%84%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    {"shop": "天丼てんや", "url": "https://news.google.com/rss/search?q=%E5%A4%A9%E4%B8%BC%E3%81%A6%E3%82%93%E3%82%84%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "don"},
    # ── ファミレス ──
    {"shop": "ガスト", "url": "https://news.google.com/rss/search?q=%E3%82%AC%E3%82%B9%E3%83%88%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ガスト", "url": "https://news.google.com/rss/search?q=%E3%82%AC%E3%82%B9%E3%83%88%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ガスト", "url": "https://news.google.com/rss/search?q=%E3%82%AC%E3%82%B9%E3%83%88%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "デニーズ", "url": "https://news.google.com/rss/search?q=%E3%83%87%E3%83%8B%E3%83%BC%E3%82%BA%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "デニーズ", "url": "https://news.google.com/rss/search?q=%E3%83%87%E3%83%8B%E3%83%BC%E3%82%BA%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "デニーズ", "url": "https://news.google.com/rss/search?q=%E3%83%87%E3%83%8B%E3%83%BC%E3%82%BA%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ロイヤルホスト", "url": "https://news.google.com/rss/search?q=%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E3%83%9B%E3%82%B9%E3%83%88%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ロイヤルホスト", "url": "https://news.google.com/rss/search?q=%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E3%83%9B%E3%82%B9%E3%83%88%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ロイヤルホスト", "url": "https://news.google.com/rss/search?q=%E3%83%AD%E3%82%A4%E3%83%A4%E3%83%AB%E3%83%9B%E3%82%B9%E3%83%88%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ココス", "url": "https://news.google.com/rss/search?q=%E3%82%B3%E3%82%B3%E3%82%B9%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ココス", "url": "https://news.google.com/rss/search?q=%E3%82%B3%E3%82%B3%E3%82%B9%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ココス", "url": "https://news.google.com/rss/search?q=%E3%82%B3%E3%82%B3%E3%82%B9%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "びっくりドンキー", "url": "https://news.google.com/rss/search?q=%E3%81%B3%E3%81%A3%E3%81%8F%E3%82%8A%E3%83%89%E3%83%B3%E3%82%AD%E3%83%BC%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "びっくりドンキー", "url": "https://news.google.com/rss/search?q=%E3%81%B3%E3%81%A3%E3%81%8F%E3%82%8A%E3%83%89%E3%83%B3%E3%82%AD%E3%83%BC%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "びっくりドンキー", "url": "https://news.google.com/rss/search?q=%E3%81%B3%E3%81%A3%E3%81%8F%E3%82%8A%E3%83%89%E3%83%B3%E3%82%AD%E3%83%BC%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ジョナサン", "url": "https://news.google.com/rss/search?q=%E3%82%B8%E3%83%A7%E3%83%8A%E3%82%B5%E3%83%B3%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ジョナサン", "url": "https://news.google.com/rss/search?q=%E3%82%B8%E3%83%A7%E3%83%8A%E3%82%B5%E3%83%B3%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "ジョナサン", "url": "https://news.google.com/rss/search?q=%E3%82%B8%E3%83%A7%E3%83%8A%E3%82%B5%E3%83%B3%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "バーミヤン", "url": "https://news.google.com/rss/search?q=%E3%83%90%E3%83%BC%E3%83%9F%E3%83%A4%E3%83%B3%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "バーミヤン", "url": "https://news.google.com/rss/search?q=%E3%83%90%E3%83%BC%E3%83%9F%E3%83%A4%E3%83%B3%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "バーミヤン", "url": "https://news.google.com/rss/search?q=%E3%83%90%E3%83%BC%E3%83%9F%E3%83%A4%E3%83%B3%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "夢庵", "url": "https://news.google.com/rss/search?q=%E5%A4%A2%E5%BA%B5%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "夢庵", "url": "https://news.google.com/rss/search?q=%E5%A4%A2%E5%BA%B5%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    {"shop": "夢庵", "url": "https://news.google.com/rss/search?q=%E5%A4%A2%E5%BA%B5%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "family"},
    # ── 麺 ──
    {"shop": "丸亀製麵", "url": "https://news.google.com/rss/search?q=%E4%B8%B8%E4%BA%80%E8%A3%BD%E9%BA%BA%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "丸亀製麵", "url": "https://news.google.com/rss/search?q=%E4%B8%B8%E4%BA%80%E8%A3%BD%E9%BA%BA%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "丸亀製麵", "url": "https://news.google.com/rss/search?q=%E4%B8%B8%E4%BA%80%E8%A3%BD%E9%BA%BA%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "はなまるうどん", "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%AA%E3%81%BE%E3%82%8B%E3%81%86%E3%81%A9%E3%82%93%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "はなまるうどん", "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%AA%E3%81%BE%E3%82%8B%E3%81%86%E3%81%A9%E3%82%93%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "はなまるうどん", "url": "https://news.google.com/rss/search?q=%E3%81%AF%E3%81%AA%E3%81%BE%E3%82%8B%E3%81%86%E3%81%A9%E3%82%93%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "富士そば", "url": "https://news.google.com/rss/search?q=%E5%AF%8C%E5%A3%AB%E3%81%9D%E3%81%B0%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "富士そば", "url": "https://news.google.com/rss/search?q=%E5%AF%8C%E5%A3%AB%E3%81%9D%E3%81%B0%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "富士そば", "url": "https://news.google.com/rss/search?q=%E5%AF%8C%E5%A3%AB%E3%81%9D%E3%81%B0%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "洋麺屋五右衛門", "url": "https://news.google.com/rss/search?q=%E6%B4%8B%E9%BA%BA%E5%B1%8B%E4%BA%94%E5%8F%B3%E8%A1%9B%E9%96%80%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "洋麺屋五右衛門", "url": "https://news.google.com/rss/search?q=%E6%B4%8B%E9%BA%BA%E5%B1%8B%E4%BA%94%E5%8F%B3%E8%A1%9B%E9%96%80%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    {"shop": "洋麺屋五右衛門", "url": "https://news.google.com/rss/search?q=%E6%B4%8B%E9%BA%BA%E5%B1%8B%E4%BA%94%E5%8F%B3%E8%A1%9B%E9%96%80%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "men"},
    # ── ラーメン ──
    {"shop": "幸楽苑", "url": "https://news.google.com/rss/search?q=%E5%B9%B8%E6%A5%BD%E8%8B%91%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "幸楽苑", "url": "https://news.google.com/rss/search?q=%E5%B9%B8%E6%A5%BD%E8%8B%91%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "幸楽苑", "url": "https://news.google.com/rss/search?q=%E5%B9%B8%E6%A5%BD%E8%8B%91%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "日高屋", "url": "https://news.google.com/rss/search?q=%E6%97%A5%E9%AB%98%E5%B1%8B%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "日高屋", "url": "https://news.google.com/rss/search?q=%E6%97%A5%E9%AB%98%E5%B1%8B%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "日高屋", "url": "https://news.google.com/rss/search?q=%E6%97%A5%E9%AB%98%E5%B1%8B%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "一風堂", "url": "https://news.google.com/rss/search?q=%E4%B8%80%E9%A2%A8%E5%A0%82%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "一風堂", "url": "https://news.google.com/rss/search?q=%E4%B8%80%E9%A2%A8%E5%A0%82%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    {"shop": "一風堂", "url": "https://news.google.com/rss/search?q=%E4%B8%80%E9%A2%A8%E5%A0%82%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "ramen"},
    # ── ピザ ──
    {"shop": "ドミノ・ピザ", "url": "https://news.google.com/rss/search?q=%E3%83%89%E3%83%9F%E3%83%8E%E3%83%94%E3%82%B6%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ドミノ・ピザ", "url": "https://news.google.com/rss/search?q=%E3%83%89%E3%83%9F%E3%83%8E%E3%83%94%E3%82%B6%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ドミノ・ピザ", "url": "https://news.google.com/rss/search?q=%E3%83%89%E3%83%9F%E3%83%8E%E3%83%94%E3%82%B6%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ピザハット", "url": "https://news.google.com/rss/search?q=%E3%83%94%E3%82%B6%E3%83%8F%E3%83%83%E3%83%88%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ピザハット", "url": "https://news.google.com/rss/search?q=%E3%83%94%E3%82%B6%E3%83%8F%E3%83%83%E3%83%88%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ピザハット", "url": "https://news.google.com/rss/search?q=%E3%83%94%E3%82%B6%E3%83%8F%E3%83%83%E3%83%88%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ピザーラ", "url": "https://news.google.com/rss/search?q=%E3%83%94%E3%82%B6%E3%83%BC%E3%83%A9%20%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ピザーラ", "url": "https://news.google.com/rss/search?q=%E3%83%94%E3%82%B6%E3%83%BC%E3%83%A9%20%E6%96%B0%E3%83%A1%E3%83%8B%E3%83%A5%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
    {"shop": "ピザーラ", "url": "https://news.google.com/rss/search?q=%E3%83%94%E3%82%B6%E3%83%BC%E3%83%A9%20%E7%99%BB%E5%A0%B4%20%E7%99%BA%E5%A3%B2&hl=ja&gl=JP&ceid=JP:ja", "category": "pizza"},
]

# =====================
# フィルター設定
# =====================
LIMITED_KEYWORDS = [
    "期間限定", "数量限定", "季節限定", "〜まで", "まで販売",
    "新発売", "復刻", "フェア", "祭り", "limited", "seasonal",
    "登場", "販売開始", "新メニュー", "新商品", "発売",
]

EXCLUDE_KEYWORDS = [
    "比較", "ランキング", "まとめ", "違い", "どっちが", "おすすめ",
    "ベスト", "人気メニュー", "全メニュー", "メニュー一覧",
    "食べてみた", "食べた感想", "実食", "レビュー", "口コミ",
    "行ってみた", "試してみた", "感想", "体験",
    "株価", "決算", "業績", "売上", "採用", "求人", "店舗数",
    "値上げ", "閉店", "倒産",
    "カロリー", "糖質", "ダイエット", "レシピ", "作り方",
    "クーポンまとめ", "割引まとめ", "画像",
    "食レポ", "PR", "CM", "タイアップ",
    "イベントレポート", "インタビュー",
    "応援", "コメント", "出演",
]

ARTICLE_MAX_AGE_DAYS = 30
DATA_FILE = "limited_menus.json"

# =====================
# ユーティリティ
# =====================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_data(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {DATA_FILE} に保存しました（{len(items)}件）")


def make_id(shop, title):
    return hashlib.md5(f"{shop}:{title}".encode()).hexdigest()


def is_valid_article(title, summary, published_str):
    text = title + " " + summary
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    if not any(kw in text for kw in LIMITED_KEYWORDS):
        return False
    if published_str:
        try:
            pub_dt = parsedate_to_datetime(published_str)
            now = datetime.now(timezone.utc)
            age = now - pub_dt.astimezone(timezone.utc)
            if age.days > ARTICLE_MAX_AGE_DAYS:
                return False
        except Exception:
            pass
    return True


def purge_old_items(items):
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


def strip_source(title):
    """「 - ニュースサイト名」を除去する"""
    idx = title.rfind(" - ")
    return title[:idx] if idx != -1 else title


def is_similar(a, b, threshold=0.31):
    return SequenceMatcher(None, a, b).ratio() >= threshold


def is_duplicate(title, existing_items):
    """既存データと類似タイトルがあるか判定する"""
    stripped = strip_source(title)
    for item in existing_items:
        if is_similar(strip_source(item["name"]), stripped):
            return True
    return False


# =====================
# Gemini AI処理
# =====================
_genai_client = None

def get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _genai_client


def enrich_with_ai(title, summary):
    client = get_genai_client()

    prompt = f"""以下は飲食チェーンの新メニューに関するニュース記事です。

タイトル: {title}
概要: {summary}

以下をJSON形式で返してください。他の文字は一切含めないでください。

{{
  "menu_name": "メニュー名（タイトルから抽出。「〇〇が登場」「〇〇を発売」の〇〇部分。どうしても不明な場合はタイトルの最初の15文字）",
  "one_liner": "このメニューの魅力を伝える一言説明（20文字以内）"
}}"""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"  AI処理エラー: {e}")
        return {"menu_name": "", "one_liner": ""}


# =====================
# フェッチ処理
# =====================

def fetch_feed(feed_config):
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

            # 今回取得分内での重複チェック
            duplicate = False
            for existing in new_items:
                if is_similar(strip_source(existing["name"]), strip_source(title)):
                    duplicate = True
                    break
            if duplicate:
                continue

            enriched = enrich_with_ai(title, summary)
            time.sleep(4)  # 60秒 ÷ 15RPM

            new_items.append({
                "id":         make_id(shop, title),
                "shop":       shop,
                "name":       title,
                "menu_name":  enriched["menu_name"],
                "one_liner":  enriched["one_liner"],
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
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] フェッチ開始")

    existing = purge_old_items(load_data())
    existing_ids = {item["id"] for item in existing}

    all_new = []
    for feed in FEEDS:
        items = fetch_feed(feed)
        new_only = [
            i for i in items
            if i["id"] not in existing_ids
            and not is_duplicate(i["name"], existing)
            and not is_duplicate(i["name"], all_new)  # ← 追加
        ]
        all_new.extend(new_only)
        # existing_idsも更新
        existing_ids.update(i["id"] for i in new_only)
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

    if "--once" in sys.argv:
        run_fetch()
    else:
        print("毎朝 8:00 に自動実行します（Ctrl+C で停止）\n")
        run_fetch()
        schedule.every().day.at("08:00").do(run_fetch)
        while True:
            schedule.run_pending()
            time.sleep(60)

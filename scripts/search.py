#!/usr/bin/env python3
"""
search.py — 按"套餐名字"模糊匹配门店餐品，可选价格区间过滤
用法：
  python search.py "板烧" --store-code 1450104
  python search.py "板烧" --store-code 1450104 --min 20 --max 30
  python search.py "豆浆" --store-code 1450104 --max 15

输出候选（productCode / 名称 / 价格），供用户挑选后再 prefs.py set。
"""
import argparse
import sys

from mcp_client import McdMcpClient


def price_of(m):
    try:
        return float(m.get("currentPrice") or 0)
    except (TypeError, ValueError):
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="套餐名字关键词，如 板烧 / 豆浆 / 吉士")
    ap.add_argument("--store-code", required=True)
    ap.add_argument("--min", type=float, default=None, dest="pmin")
    ap.add_argument("--max", type=float, default=None, dest="pmax")
    args = ap.parse_args()

    c = McdMcpClient()
    meals = c.query_meals(args.store_code)
    q = args.query.strip()

    # 1) 子串匹配
    hits = [(code, m) for code, m in meals.items() if q and q in (m.get("name") or "")]
    # 2) 兜底：关键词的每个字都出现在名称里（宽松模糊）
    if not hits:
        qs = set(q)
        hits = [(code, m) for code, m in meals.items() if qs and qs <= set(m.get("name") or "")]

    # 价格区间
    def keep(m):
        p = price_of(m)
        if args.pmin is not None and p < args.pmin:
            return False
        if args.pmax is not None and p > args.pmax:
            return False
        return True

    hits = [(code, m) for code, m in hits if keep(m)]
    hits.sort(key=lambda x: price_of(x[1]))

    if not hits:
        rng = f"（价格区间 ¥{args.pmin or 0}–{args.pmax or '不限'}）" if (args.pmin or args.pmax) else ""
        print(f"没有找到包含「{q}」的餐品{rng}。可换个关键词，或放宽价格区间。")
        return 1

    print(f"找到 {len(hits)} 个「{q}」相关餐品：\n")
    for i, (code, m) in enumerate(hits, 1):
        p = price_of(m)
        stock = "" if m.get("canWithOrder", True) else "（当前不可下单）"
        print(f"{i}. {m.get('name')}  ¥{p:.1f}  [{code}]{stock}")
    print("\n选好后用：python prefs.py set ... --meal <productCode>:1")
    return 0


if __name__ == "__main__":
    sys.exit(main())

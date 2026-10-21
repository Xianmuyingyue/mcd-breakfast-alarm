#!/usr/bin/env python3
"""
prefs.py — 早餐闹钟配置（WorkBuddy 持久化）
存储：~/.workbuddy/mcd_breakfast_alarm/prefs.json（仅本机，不入仓库）

用法：
  python prefs.py set --store-code 1450104 --store-name "麦当劳上海黄浦悦荟广场餐厅" \
      --time 07:20 --meal 1406:1 --meal 9900005460:1 --days weekdays
  python prefs.py show
  python prefs.py clear
"""
import argparse
import json
import os
import sys
from datetime import datetime

DIR = os.path.expanduser("~/.workbuddy/mcd_breakfast_alarm")
STORE = os.path.join(DIR, "prefs.json")


def load():
    if os.path.exists(STORE):
        try:
            return json.load(open(STORE, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save(d):
    os.makedirs(DIR, exist_ok=True)
    json.dump(d, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def parse_meal(s):
    code, _, qty = s.partition(":")
    return {"productCode": code, "quantity": int(qty or 1)}


def main():
    ap = argparse.ArgumentParser(description="早餐闹钟配置")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("set")
    s.add_argument("--store-code", required=True)
    s.add_argument("--store-name", required=True)
    s.add_argument("--time", required=True, help="HH:MM，如 07:20")
    s.add_argument("--meal", action="append", default=[], help="productCode:qty，可重复")
    s.add_argument("--days", default="daily", choices=["daily", "weekdays"])
    s.add_argument("--enabled", default="true")
    sk = sub.add_parser("skip")
    sk.add_argument("--date", required=True, help="YYYY-MM-DD")
    us = sub.add_parser("unskip")
    us.add_argument("--date", required=True, help="YYYY-MM-DD")
    sub.add_parser("show")
    sub.add_parser("clear")
    args = ap.parse_args()

    if args.cmd == "set":
        d = load()
        d.update({
            "storeCode": args.store_code,
            "storeName": args.store_name,
            "time": args.time,
            "days": args.days,
            "enabled": str(args.enabled).lower() != "false",
            "meal": [parse_meal(m) for m in args.meal],
            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        save(d)
        print("✅ 已设置早餐闹钟")
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "skip":
        d = load()
        d.setdefault("skipDates", [])
        if args.date not in d["skipDates"]:
            d["skipDates"].append(args.date)
        save(d)
        print(f"已取消 {args.date} 的早餐（该日不建单）")
        return 0
    if args.cmd == "unskip":
        d = load()
        d["skipDates"] = [x for x in d.get("skipDates", []) if x != args.date]
        save(d)
        print(f"已恢复 {args.date} 的早餐")
        return 0
    if args.cmd == "show":
        d = load()
        print(json.dumps(d, ensure_ascii=False, indent=2) if d else "（未设置）请先运行 prefs.py set ...")
        return 0
    if args.cmd == "clear":
        save({})
        print("已清空早餐闹钟配置")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
fire.py — 早餐闹钟触发
流程：读配置 → 确认餐品在售 → 核价 → 创建「待支付」订单 → 输出付款提醒

用法：
  python fire.py            # 真实建单（待支付、不扣款）
  python fire.py --dry-run  # 只核价，不下单

说明：麦当劳 MCP 没有「预约下单 / 定时下单」接口，
本脚本由 WorkBuddy 的定时自动化在设定时刻触发，属于「到点现下」，
因此订单生成后需在 15 分钟内于麦当劳 App 付款。
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import McdMcpClient  # noqa: E402
from blessing import today_blessing  # noqa: E402

DIR = os.path.expanduser("~/.workbuddy/mcd_breakfast_alarm")
STORE = os.path.join(DIR, "prefs.json")


def load():
    if not os.path.exists(STORE):
        return None
    try:
        return json.load(open(STORE, encoding="utf-8"))
    except Exception:
        return None


def save(d):
    os.makedirs(DIR, exist_ok=True)
    json.dump(d, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    p = load()
    if not p:
        print("❌ 还没设置早餐闹钟。请先运行：\n"
              "python prefs.py set --store-code <店号> --store-name \"<店名>\" "
              "--time 07:20 --meal <productCode>:1")
        return 2
    if not p.get("enabled", True):
        print("⏸ 早餐闹钟已暂停（prefs.enabled=false）")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    if today in (p.get("skipDates") or []):
        p["skipDates"] = [x for x in p["skipDates"] if x != today]
        save(p)
        print(f"⏭ {today} 的早餐已取消（不建单），本次跳过。")
        return 0

    c = McdMcpClient()
    meals = c.query_meals(p["storeCode"])
    items = []
    for it in p.get("meal", []):
        code = str(it["productCode"])
        if code not in meals:
            print(f"⚠️ 餐品 {code} 当前不在售，本次跳过。请先用 query-meals 查可用餐品后更新配置。")
            return 3
        items.append({"productCode": code, "quantity": int(it.get("quantity", 1))})

    pr = c.calculate_price(items, p["storeCode"])
    d = (pr.get("structuredContent", {}) or {}).get("data", {}) or {}
    amount = d.get("price")
    yuan = f"¥{amount / 100:.0f}" if isinstance(amount, (int, float)) else "见 App"

    if args.dry_run:
        print(f"[dry-run] {p['storeName']} · {p['time']} · 预计实付 {yuan}（未下单）")
        return 0

    payload = {
        "storeCode": p["storeCode"],
        "orderType": 1,
        "beType": 1,
        "takeWayCode": "eat-in",
        "needTableware": False,
        "items": items,
    }
    r = c.create_order(payload)
    sc = (r or {}).get("structuredContent", {}) or {}
    if not sc.get("success"):
        msg = sc.get("message") or ""
        code = str(sc.get("code") or "")
        if code == "600039" or "上限" in msg:
            print("⚠️ 今日下单次数已达上限（600039），明天再试——这不是餐品问题。")
        else:
            print(f"❌ 下单失败（{code}）：{msg}")
        return 4

    data = sc.get("data", {}) or {}
    od = data.get("orderDetail", {}) or data
    order_id = data.get("orderId") or od.get("orderId")
    meal_txt = "、".join(f"{meals.get(i['productCode'], {}).get('name', i['productCode'])}×{i['quantity']}"
                         for i in items)

    print(f"""
☀️ 早餐已备好 · {p['storeName']}
────────────────────────
套餐：{meal_txt}
金额：{yuan}（待支付）
订单：{order_id}
────────────────────────
👉 请在 15 分钟内打开「麦当劳 App → 我的订单 → 付款」，到店取餐即可。
────────────────────────
麦言麦语｜{today_blessing()}
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())

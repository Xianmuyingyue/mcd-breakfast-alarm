#!/usr/bin/env python3
"""
blessing.py — 麦言麦语（每日一句祝福）
每天固定一句、按日期确定性选取（同一天多次运行结果一致）；
可随付款提醒一起推送。

用法：
  python blessing.py                 # 今天的麦言麦语
  python blessing.py --date 2026-10-22
  python blessing.py --random        # 随机一句（测试用）
"""
import argparse
import hashlib
import sys
from datetime import datetime

BLESSINGS = [
    "早餐不是一天的开始，是你愿意对自己好的第一个证据。",
    "先把自己喂饱，世界的事才轮得到你操心。",
    "热气腾腾的早餐，是成年人最便宜的重启键。",
    "你可以拒绝很多事，但别拒绝好好吃早饭。",
    "日子再赶，也值得为一口热的停三分钟。",
    "不是每一天都要赢，但每一天都值得吃顿好的。",
    "把早餐吃好，是对生活最小的反抗。",
    "你负责出发，我负责把热的那份备好。",
    "有些温暖不用等，比如一份提前订好的早餐。",
    "决定权在你，备好的那份在我。",
    "吃不吃由你，但我会先替你订上。",
    "早上的一口热，抵得过一整天的慌。",
    "别急着成为谁，先好好吃顿早饭。",
    "生活的答案，常常藏在一份热早餐里。",
    "你不必每天都坚强，但可以每天都吃早餐。",
    "把复杂留给世界，把早餐留给自己。",
    "热豆浆会凉，但被惦记的感觉不会。",
    "早起不一定自律，但吃早餐一定温柔。",
    "你走过的每一步，都需要一点热量。",
    "早餐是一天里，最容易兑现的承诺。",
    "别让忙碌替你决定，今天也要好好吃饭。",
    "愿意为自己准备早餐的人，运气不会太差。",
    "世界很大，先吃好眼前这一口。",
    "慢慢来，热的那份我一直给你留着。",
    "今天不必完美，吃顿热乎的就很了不起。",
    "早餐的温度，决定一天的态度。",
    "你只管往前走，早餐这件小事交给我。",
    "把胃照顾好，心才有地方安放。",
    "每一个认真吃早餐的早晨，都值得被记住。",
    "醒来的第一件事，是允许自己好好生活。",
]


def today_blessing(date: str | None = None, random_pick: bool = False) -> str:
    if random_pick:
        import random
        return random.choice(BLESSINGS)
    date = date or datetime.now().strftime("%Y-%m-%d")
    idx = int(hashlib.md5(date.encode("utf-8")).hexdigest(), 16) % len(BLESSINGS)
    return BLESSINGS[idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD，默认今天")
    ap.add_argument("--random", action="store_true")
    args = ap.parse_args()
    print(f"麦言麦语｜{today_blessing(args.date, args.random)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

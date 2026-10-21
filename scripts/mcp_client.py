#!/usr/bin/env python3
"""
douyue-mcd-coach · 麦当劳官方 MCP 客户端 (mcp_client.py)
------------------------------------------------------
通过麦当劳中国官方 MCP（Streamable HTTP）获取真实菜单与营养数据。

安全约定：
  - Token 仅从环境变量 MCD_MCP_TOKEN 读取，绝不写入代码 / 提交仓库；
  - 本文件不含任何真实 Token。

核心能力：
  - list_nutrition_foods()：解析 list-nutrition-foods 的 TOON 紧凑格式，
    返回结构化营养列表（产品名 / 能量kJ / 能量kcal / 蛋白 / 脂肪 / 碳水 / 钠 / 钙）。
  - call_tool(name, arguments)：通用工具调用（query-meal-detail / calculate-price 等）。

仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

MCP_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2024-11-05"


class McdMcpClient:
    """麦当劳 MCP Streamable HTTP 客户端。"""

    def __init__(self, token: str | None = None, url: str = MCP_URL,
                 timeout: int = 30):
        self.token = token or os.environ.get("MCD_MCP_TOKEN")
        if not self.token:
            raise RuntimeError(
                "缺少 MCD_MCP_TOKEN：请先 export MCD_MCP_TOKEN=你的Token"
            )
        self.url = url
        self.timeout = timeout
        self._session: str | None = None
        self._seq = 0
        self._handshake()

    # ---------- 底层传输 ----------
    def _post(self, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        req = urllib.request.Request(
            self.url, data=data, headers=headers, method="POST"
        )
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"MCP HTTP {e.code}: {body[:500]}") from e
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self._session = sid
        raw = resp.read().decode("utf-8", "replace")
        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: str) -> dict:
        """兼容直接 JSON 与 SSE(text/event-stream) 两种返回。"""
        raw = raw.strip()
        if raw.startswith("{"):
            return json.loads(raw)
        # SSE：提取最后一个 data: 行里的 JSON
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[len("data:"):].strip()
                if chunk.startswith("{"):
                    return json.loads(chunk)
        raise RuntimeError("无法解析 MCP 返回：" + raw[:300])

    def _handshake(self) -> None:
        self._seq += 1
        r = self._post({
            "jsonrpc": "2.0", "id": self._seq, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "douyue-mcd-coach", "version": "0.1"},
            },
        })
        # 发送 initialized 通知（无需响应）
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            pass

    # ---------- 工具调用 ----------
    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        self._seq += 1
        r = self._post({
            "jsonrpc": "2.0", "id": self._seq, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })
        return r.get("result", {})

    # ---------- 业务方法 ----------
    def list_nutrition_foods(self) -> list[dict]:
        """返回结构化营养列表（真实官方数据）。"""
        result = self.call_tool("list-nutrition-foods", {})
        text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        return self.parse_toon(text)

    @staticmethod
    def _extract_inner_json(text: str) -> dict:
        """
        list-nutrition-foods 的 text 是一段 Markdown，其中
        '## Original Response' 之后内嵌了一份真实 API 返回的 JSON
        （含 data 字段，值为 TOON 字符串，内部换行被转义为 \\n）。
        这里用括号配平抽取出这份 JSON 并解析。
        """
        start = text.find('{"success"')
        if start == -1:
            start = text.find("{")
        if start == -1:
            raise RuntimeError("未在返回中定位到原始响应 JSON")
        depth = 0
        in_str = False
        esc = False
        end = None
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
        if end is None:
            raise RuntimeError("原始响应 JSON 括号不匹配")
        return json.loads(text[start:end])

    @staticmethod
    def parse_toon(text: str) -> list[dict]:
        """
        解析 list-nutrition-foods 的 TOON 紧凑格式，例如：
          [160]{productName,nutritionDescription,energyKj,energyKcal,
                protein,fat,carbohydrate,sodium,calcium}:
            猪柳麦满分,null,1288,308,16,16,24,781,213
        返回每条餐品的字段字典；数值字段转为 int/float，null 转 None。
        """
        # text 内嵌一份原始 JSON，先解析出 data 字段（TOON 字符串）
        try:
            inner = McdMcpClient._extract_inner_json(text)
            toon = inner.get("data", "")
            if isinstance(toon, str) and toon.strip():
                text = toon
        except Exception:
            # 若已是纯 TOON，则直接使用
            pass
        m = re.search(r"\[(\d+)\]\{([^}]*)\}:(.*)", text, re.DOTALL)
        if not m:
            raise RuntimeError("未在返回中识别 TOON 格式")
        fields = [f.strip() for f in m.group(2).split(",")]
        body = m.group(3).strip()
        rows: list[dict] = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != len(fields):
                # 个别品名可能含逗号，尽力容错：跳过长度不符的行
                continue
            item: dict = {}
            for key, val in zip(fields, parts):
                if val == "" or val.lower() == "null":
                    item[key] = None
                else:
                    try:
                        item[key] = int(val)
                    except ValueError:
                        try:
                            item[key] = float(val)
                        except ValueError:
                            item[key] = val
            rows.append(item)
        return rows

    def find_food(self, keyword: str) -> dict | None:
        """按关键字模糊匹配营养列表中的第一条。"""
        for f in self.list_nutrition_foods():
            if keyword in (f.get("productName") or ""):
                return f
        return None

    # ---------- 执行链路（领券 / 核价 / 下单） ----------
    def auto_bind_coupons(self) -> dict:
        """自动领取当前可领的全部优惠券（免费、零资金风险，默认可执行）。"""
        return self.call_tool("auto-bind-coupons", {})

    def query_nearby_stores(self, city: str, keyword: str,
                            be_type: int = 1) -> list:
        """
        查询到店门店（实测：需 city + keyword 同时提供，searchType=2）。
        返回 data 列表，每项含 storeName / storeCode / beCode / distance。
        最近门店的 storeCode 可继续传给 query_meals / calculate_price / create_order。
        """
        r = self.call_tool("query-nearby-stores", {
            "beType": be_type, "searchType": 2,
            "city": city, "keyword": keyword,
        })
        return (r.get("structuredContent") or {}).get("data") or []

    def query_meals(self, store_code: str, order_type: int = 1,
                    be_type: int = 1) -> dict:
        """
        查询门店在售餐品，返回 data.meals（code → {name, currentPrice, canWithOrder}）。
        canWithOrder=True 的套餐/单品方可直接进入下单链路。
        """
        r = self.call_tool("query-meals", {
            "storeCode": store_code, "orderType": order_type, "beType": be_type,
        })
        return ((r.get("structuredContent") or {}).get("data") or {}).get("meals") or {}

    def calculate_price(self, items: list, store_code: str,
                        order_type: int = 1, be_type: int = 1,
                        be_code: str | None = None) -> dict:
        """
        核价。items 为餐品列表，每项为（注意字段是 productCode，不是 code）：
            {"productCode": "<餐品code>", "quantity": <n>,
             "modification": {"values": [...]}(可选),
             "couponId"/"couponCode": "(可选，带券核价)"}
        be_type=1 到店自取；外送/得来速需 beCode。order_type=1 到店。
        返回 data.price / originalPrice / discount，单位均为「分」（如 4800 = ¥48）。
        """
        args = {"storeCode": store_code, "orderType": order_type,
                "beType": be_type, "items": items}
        if be_code:
            args["beCode"] = be_code
        return self.call_tool("calculate-price", args)

    def create_order(self, arguments: dict) -> dict:
        """
        生成真实订单（涉及资金，调用方须确保已完成二次确认）。
        arguments 按 create-order 的 inputSchema 组装，至少含
        storeCode / orderType / items。
        """
        return self.call_tool("create-order", arguments)


if __name__ == "__main__":
    # 简易自检：打印关键品项的真实热量
    client = McdMcpClient()
    foods = client.list_nutrition_foods()
    print(f"共获取 {len(foods)} 条营养数据")
    for kw in ("板烧鸡腿堡", "蔬菜杯", "双层吉士汉堡", "吉士汉堡包"):
        f = client.find_food(kw)
        if f:
            print(f"  {f['productName']}: {f['energyKcal']} kcal, "
                  f"蛋白 {f['protein']}g")
        else:
            print(f"  （未找到）{kw}")

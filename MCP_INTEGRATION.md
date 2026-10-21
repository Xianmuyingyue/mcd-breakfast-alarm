# MCP 集成说明 · 麦麦早餐闹钟

## 使用的麦当劳 MCP Server
- URL：`https://mcp.mcd.cn`（Streamable HTTP）
- 鉴权：`Authorization: Bearer <MCD_MCP_TOKEN>`

## 调用的 Tool 与用途

| Tool | 用途 |
|---|---|
| `query-nearby-stores` | 首次设置时帮用户找常去门店，拿 `storeCode` |
| `query-meals` | 确认配置的早餐餐品**当前仍在售**，并取名称 |
| `calculate-price` | 下单前核价（金额单位：**分**，如 2400 = ¥24） |
| `create-order` | 创建「待支付」订单（**不扣款**） |
| `query-order` / `cancel-order` | 可选：查单 / 取消（用户改主意时） |

## 调用流程

```
prefs.json（店 / 时间 / 套餐）
        │
        ▼
query-meals(storeCode)  ── 餐品在售？ ── 否 → 跳过并提示更新套餐
        │ 是
        ▼
calculate-price(items, storeCode)  → 实付金额
        │
        ▼
create-order({storeCode, orderType:1, beType:1, takeWayCode:"eat-in", items})
        │
        ▼
输出付款提醒（门店/套餐/金额/订单号/15 分钟）
        │
        ▼
用户在「麦当劳 App → 我的订单」付款 → 到店取餐
```

## 关键实测结论（2026-10）
- 营养数据来自 `list-nutrition-foods`（板烧鸡腿堡 391 kcal / 23g）。
- `calculate-price` 金额单位是**分**，返回多项金额，建议逐项对账。
- `create-order` 只生成「待支付」，**不扣款**；支付在 App 完成。
- `payH5Url` 是「扫码中间页」，手机直开要截图再扫；**正解是 App 我的订单直接付款**。
- `600039`＝账号级「每日下单次数已达上限」，与餐品无关，明天再试。
- `auto-bind-coupons` 常返回 `499`（无券），不是失败。

## 业务价值
- **时间价值**：把"到点才想起来点单"变成"到点单已备好"，减少早餐时段的决策与排队。
- **场景绑定**：通勤（打工人）/ 早八（学生），高频、可养成习惯。
- **合规**：不代付、不锁库存、不夸大"预约"，只做"定时建单 + 付款提醒"。

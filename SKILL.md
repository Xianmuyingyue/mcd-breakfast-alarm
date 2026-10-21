---
name: mcd-breakfast-alarm
slug: mcd-breakfast-alarm
version: 1.0.0
displayName: 麦麦早餐闹钟
description: 给打工人/学生设一个"早餐闹钟"：到点用麦当劳官方 MCP 建好「待支付」早餐单并推送付款提醒，到店取餐即可。卖的不是"吃什么"，而是"到点单已备好、你只差付款"的时间。
---

# 麦麦早餐闹钟 · mcd-breakfast-alarm

## 一句话
把"每天早上手忙脚乱点早餐"变成**一次设置、到点提醒付款**：到点自动建好「待支付」订单，你走到麦当劳只差掏手机付一下。

> 诚实边界：麦当劳 MCP **没有预约/定时下单接口**。本 Skill 的做法是——用 **WorkBuddy 的定时自动化**在设定时刻触发，**现场创建待支付订单**，再提醒你付款。所以它是「**定时建单 + 付款提醒**」，不是"提前锁单"。订单 15 分钟内需付款。

## 适用人群
- 打工人：通勤路上到店取早餐，不想排队点单；
- 学生：早八赶时间，起床就能顺手付款。

## 工作流程

### 1. 首次设置：模糊找套餐 + 选价格区间
- 问用户"想吃什么"，**允许只说名字**（如"板烧""豆浆""吉士""鸡腿"）；
- 用模糊匹配列出候选：
  ```bash
  python scripts/search.py "板烧" --store-code <店号>
  python scripts/search.py "板烧" --store-code <店号> --min 20 --max 30
  ```
  输出候选（名称 / 价格 / `productCode`）；
- 候选多时，**提示用户选一个价格区间**再筛一次；
- 用户选定后写入：
  ```bash
  python scripts/prefs.py set --store-code <店号> --store-name "<店名>" \
    --time 07:20 --meal <productCode>:1 --days weekdays
  ```
- 回读确认：`python scripts/prefs.py show`。

### 2. 每晚确认（默认订 / 可改 / opt-out）
每晚（如 20:00）由定时任务提醒：
> 「明天 07:20 的早餐，默认：<店> <套餐>，要改或取消吗？」

- 用户回"**不订/取消**" → `python scripts/prefs.py skip --date <明天>`
- 用户回"**改…**" → 按新选择重新 `prefs.py set ...`
- **无论回不回答，默认都订**；只有明确说"不订/取消"才跳过。

### 3. 次日到点下单 + 支付提醒
07:20 定时任务运行 `python scripts/fire.py`：
- 若当天在 `skipDates` → **跳过、不建单**；
- 否则 → 确认在售 → 核价 → 建「待支付」单 → 输出付款提醒（门店/套餐/金额/订单号/15 分钟）。
- 预演：`python scripts/fire.py --dry-run`（只核价、不下单）。

### 4. 付款，或者——不付
- 付款：麦当劳 App「我的订单」→ 付款 → 到店取餐；
- **不付也不会扣钱**：待支付单 **15 分钟自动过期**，等于"自动取消"——这是本方案的安全垫。
> 不要在手机上直接打开 `payH5Url`（扫码中间页，同机扫不了自己屏幕）。

### 5. 改 / 停
- 改：重新 `prefs.py set ...`（覆盖）；
- 停某天：`prefs.py skip --date <日期>`；恢复：`prefs.py unskip --date <日期>`；
- 长期停：`prefs.py set ... --enabled false`，或 `prefs.py clear`。

## 硬性原则（务必遵守）
1. **不代付**：本 Skill 只建「待支付」单，**绝不**代替用户付款；付款一律由用户在麦当劳 App 完成。
2. **首次设置要确认**：门店 / 时间 / 套餐，三样都让用户明确确认后再保存。
3. **15 分钟时限**：提醒里必须写"15 分钟内付款"，否则订单过期。
4. **`600039` 处理**：返回"今日下单数已达上限"时，如实告知"明天再试"，**不要换单硬刷**。
5. **餐品下架**：`query-meals` 里找不到配置的餐品时，跳过本次并提示更新套餐，不要乱下别的。
6. **不夸大**：对外描述用「定时建单 + 付款提醒」，**不要**说"自动预约 / 自动下单 / 自动付款"。

## 可选：WorkBuddy 定时自动化（手动开启）
见 `docs/automation.md`。核心是设一个"每天 HH:MM"的定时任务，prompt 让 Agent 运行 `python scripts/fire.py` 并把输出发给用户。
> 默认不自动开启；用户需要时再建。

## 目录
```
mcd-breakfast-alarm/
├── SKILL.md
├── README.md
├── MCP_INTEGRATION.md
├── mcp-config.example.json
├── scripts/
│   ├── prefs.py       配置：店/时间/套餐
│   ├── fire.py        触发：核价 → 建待支付单 → 付款提醒
│   └── mcp_client.py  官方 MCP 客户端
└── docs/automation.md 定时自动化配置说明
```

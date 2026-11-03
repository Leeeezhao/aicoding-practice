# 题目：多端早餐店订单系统

> **来源标签**：来自公开复盘改写，非官方题库  
> **参考**：蚂蚁 AI Coding 2026-03-29 公开复盘（叫号牌/顾客/店主三端 + 订单状态机）  
> 链接见 `SOURCES.md`

## 背景

实现一个内存型 HTTP 订单服务，模拟早餐店从下单到支付的流程。考试常见形态是「一个中心服务 + 多个终端」；本练习先把 **服务端 API + 状态机** 做对（终端可用 curl 代替 TUI）。

## 必做（P0）

启动：

```bash
python starter/server.py --port 8025
```

### 状态机（不可跳级）

```
PENDING → CONFIRMED → COOKING → READY → PAID
            ↘ CANCELLED（仅 PENDING/CONFIRMED 可取消）
```

### API（路径与字段名请保持一致，便于判题）

| Method | Path | 说明 |
|--------|------|------|
| GET | `/menu` | 返回菜单列表 |
| POST | `/orders` | 创建订单，body: `{"items":[{"id":"baozi","qty":2}],"customer":"Alice"}` |
| GET | `/orders` | 全部订单 |
| GET | `/orders/{id}` | 单个订单 |
| PUT | `/orders/{id}/status` | body: `{"status":"CONFIRMED","token":"..."}` |

规则：

1. 创建后状态为 `PENDING`，分配递增整数 `id`（从 1 起）。
2. 非法状态跳转返回 HTTP 400，且 **不修改** 原状态。
3. 更新状态需要 `token == shop-owner`（店主口令）；缺 token / 错 token → 403。
4. `CANCELLED` 与 `PAID` 为终态。
5. 菜单至少包含：`baozi`(包子)、`youtiao`(油条)、`doujiang`(豆浆)。
6. 提供 `POST /reset` 清空所有订单（方便反复自测）。

## 验收

```bash
python -m pytest tests/ -q
```

公开测例会检查：主链路、非法跳转无副作用、权限、重置。

## 交付物

- 可运行服务代码
- `DELIVERY.md`：状态机说明、如何用 curl 走通一单
- （可选）三个终端脚本 / 简易 TUI

## 加分项

- SQLite 持久化（重启不丢单）
- 叫号牌轮询展示脚本
- 并发下 id 不冲突

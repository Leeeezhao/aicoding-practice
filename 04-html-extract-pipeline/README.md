# 题目：脏 HTML 商品字段批处理 Pipeline

> **来源标签**：来自公开复盘改写，非官方题库  
> **参考**：蚂蚁 AI Coding 公开复盘中的「网页数据提取与清洗 Pipeline」类题  
> 链接：https://onefly.top/posts/ant-ai-coding-interview-guide.html

## 背景

`data/html_samples/` 下有一批结构不一致、编码/脏数据混杂的 HTML 片段。请实现可批处理、可观测、可扩展的提取清洗流水线。

## 必做（P0）

从每个 HTML 尽量提取：

- `product_name`
- `price`（float）
- `currency`（如 CNY / USD）
- `stock`（int；文本「有货/缺货」需映射）

并对 **每个文件** 产出一条记录（成功或失败都要保留），最后写：

- `output/results.jsonl`：一行一条 JSON
- `output/summary.json`：成功数、失败数、按错误码计数

入口：

```bash
python starter/main.py --input data/html_samples --output-dir output
```

### 记录格式

```json
{
  "source_file": "001.html",
  "status": "success",
  "product_name": "Example Phone",
  "price": 2999.0,
  "currency": "CNY",
  "stock": 12,
  "errors": []
}
```

失败时 `status=failed`，`errors` 放入稳定错误码，例如：`missing_price` / `parse_error` / `invalid_stock`。

### 硬约束

1. **单条失败不得导致整个进程退出。**
2. 价格可能含 `¥`、`$`、千分位、空格。
3. 货币别名：`人民币`/`CNY`/`¥` → `CNY`；`$`/`USD` → `USD`。
4. 库存：`有货`→可用正数或约定值；`缺货`/`暂时售罄`→0。
5. 输出文件名排序稳定（按 `source_file` 字典序处理）。

## 验收

```bash
python -m pytest tests/ -q
```

## 交付物

- 源码
- `DELIVERY.md`：分层设计（发现/解析/归一化/写出）、错误码表、已知限制

## 加分项

- 线程/进程池加速，但保持结果确定性
- 更丰富的错误分类与样例回归测试

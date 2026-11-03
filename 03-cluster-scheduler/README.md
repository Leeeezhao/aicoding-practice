# 题目：集群调度策略模拟器

> **来源标签**：来自公开面经改写，非官方题库  
> **参考帖**：牛客「4.2蚂蚁ai coding题目」——集群调度策略模块设计和模拟  
> 链接：https://www.nowcoder.com/feed/main/detail/daf318b10f2f410fa3a14e2bf8f1967d

## 目标

实现一个 **Scheduler + Simulator**，在动态负载与故障条件下平衡：

- 高优作业低延迟
- 集群利用率
- 普通作业公平性

## 场景设定（简化可跑版）

- 集群有 `M` 台同质机器（每台容量 1 个 slot；占用即独占）。
- 时间用整数分钟推进：`simulator` 每步 +1。
- 作业字段：`job_id`, `priority`(`normal`|`high`), `resource_num`, `submit_time`, `estimated_time`, `actual_time`（实际时长，可与估计差 ±20%）。
- 可选事件：`failures` —— 某时刻某台机器故障，维修 `repair_minutes`（默认 24*60，样例可用更小值）。

## 必做运行规则

1. 作业绑定到足够空闲机器后才能运行；运行中机器被占用。
2. 作业可能成功结束；若因机器故障中断：占用机器进入维修，作业回队列重试。
3. **允许抢占**：`high` 可抢占正在跑的 `normal`；被抢占作业回队列，并在剩余时长上 **额外 +10** 分钟成本。
4. 输出可复盘事件日志，并统计：
   - 高优作业平均等待、P95 等待
   - 集群利用率（忙碌机器时间 / 总机器时间）
   - 普通作业公平性：最长等待、等待方差、饥饿作业数（等待 > 阈值）

## 输入 / 输出

```bash
python starter/main.py \
  --cluster sample_data/cluster.json \
  --jobs sample_data/jobs.jsonl \
  --events sample_data/events.jsonl \
  --strategy priority_preempt \
  --output output/report.json
```

`report.json` 至少包含：`metrics`, `baseline_metrics`（与 FIFO 对比）, `events_sample`。

## 验收场景（自测也必须覆盖）

1. 基线对比：至少与 FIFO 对比
2. 波峰：批量 normal + 高频 high 插队
3. 故障场景
4. 抢占场景
5. 同一输入多次运行指标一致（可复现）

```bash
python -m pytest tests/ -q
```

## 交付物

- 调度器与模拟器源码
- 策略说明（为何这样设计）
- 指标报告
- 已知问题与下一步优化

## 加分项

- 可插拔策略框架
- 根据拥塞动态调参
- 更精细的抢占成本建模

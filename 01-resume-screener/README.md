# 题目：简历筛选与排序助手

> **来源标签**：来自公开面经/复盘改写，非官方题库  
> **参考帖**：蚂蚁 AI Coding 面经（牛客：简历筛选排序、`result.json` 交付）  
> 链接见仓库根目录 `SOURCES.md`

## 背景

你需要实现一个命令行简历筛选助手：读取一批 Markdown 简历与一份职位要求，完成特征提取、同义词归一化、评分与排序，输出 `result.json`。

## 输入

- `data/job.md`：职位要求（技能、年限、学历、地点等）
- `data/resumes/*.md`：候选人简历（结构不完全统一）

## 必做功能（P0）

1. **特征提取器**：从简历中尽量抽取：姓名、技能列表、工作年限（可估算）、学历、期望/所在城市、项目关键词。
2. **归一化**：处理同义词，例如 `k8s`/`kubernetes`、`js`/`javascript`、`pytorch`/`torch` 视为同一技能；城市别名如 `帝都`→`北京`。
3. **评分器**：至少包含可解释的多维分数（建议：技能命中、年限、学历、地点），再合成 `overall_score`（0~1）。
4. **排序输出**：按 `overall_score` 降序写入 `result.json`。
5. **可运行入口**：

```bash
python starter/main.py --job data/job.md --resumes data/resumes --output result.json
```

## 输出格式（必须）

```json
{
  "job_title": "后端开发工程师",
  "candidates": [
    {
      "file": "zhangsan.md",
      "name": "张三",
      "overall_score": 0.86,
      "skill_score": 0.9,
      "experience_score": 0.8,
      "education_score": 1.0,
      "location_score": 1.0,
      "matched_skills": ["Python", "Kubernetes"],
      "missing_skills": ["Go"],
      "reason": "一句话解释"
    }
  ]
}
```

约束：

- `candidates` 必须覆盖输入目录中所有 `.md` 简历（即使低分也要入榜）。
- 分数为有限浮点数，建议保留 2~4 位小数。
- 不得依赖外网大模型 API（考试常断网）；可用规则/词典完成。

## 验收方式

- 运行入口命令不崩溃。
- `python -m pytest tests/ -q` 通过公开样例断言（字段存在、排序正确、同义词命中）。
- 自行补充异常样例：空简历、缺字段、乱码技能名。

## 交付物

- 可运行源码（可在 `starter/` 内修改）
- `result.json` 样例输出
- 简短 `DELIVERY.md`：说明评分公式、同义词表、已知限制

## 加分项（P2）

- 可配置权重的 `config.json`
- 对低分候选人给出改进建议
- 单元测试覆盖同义词与学历映射边界

# 题库结构与数据规范

本文档说明 `index.html` 内嵌题库的数据结构，供贡献者扩充题库时参考。

## 1. 数据总览

题库以单个 JS 对象 `BANK` 的形式内嵌在 `index.html` 的 `<script>` 中：

```js
const BANK = {
  meta: { ... },        // 元信息：来源、题型统计、章节、解析统计、考试蓝图
  questions: [ ... ]    // 题目数组
};
const QUESTIONS = BANK.questions;
const CHAPTERS = BANK.meta.chapters;
```

---

## 2. `meta` 字段

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `sources` | `string[]` | 题库来源资料名称列表 |
| `counts` | `object` | 各题型题量统计 `{single, multiple, judge, short, fill, essay}` |
| `chapters` | `string[]` | 章节名称，**必须包含全部 5 章** |
| `parse_stats` | `object` | 解析过程统计（丢弃块数、无答案数、自动补答案数） |
| `exam` | `object` | 课程考试蓝图 |

### `exam` 结构

```js
exam: {
  date: "2026-10-17",      // 考试日期
  duration_min: 60,        // 考试时长（分钟）
  blueprint: [             // 题型蓝图
    { type: "single",   count: 20, score: 2  },
    { type: "multiple", count: 10, score: 3  },
    { type: "short",    count: 2,  score: 5  },
    { type: "essay",    count: 1,  score: 20 }
  ]
}
```

---

## 3. 题目字段规范

### 通用字段

| 字段 | 必填 | 类型 | 说明 |
| :--- | :--- | :--- | :--- |
| `type` | ✅ | `string` | 题型，见下方题型表 |
| `stem` | ✅ | `string` | 题干 |
| `id` | ✅ | `string` | 唯一 ID，格式 `q` + 5 位零填充，如 `q00001` |
| `chapter` | ✅ | `string` | 所属章节，**须落在 `meta.chapters` 中** |
| `explain` | 建议 | `string` | 答案解析 / 采分点提示 |
| `source` | 建议 | `string` | 题目来源资料 |

### 客观题（`single` / `multiple` / `judge`）

```js
{
  "type": "single",
  "stem": "我国属于____国防",
  "options": ["扩张型", "自卫型", "联盟型", "中立型"],
  "answer": "B",              // single/judge：单个字母；multiple：多字母无分隔，如 "ABD"
  "explain": "我国是社会主义国家，奉行独立自主的和平外交政策，国防属于自卫型。",
  "source": "10.3军理200单选+100多选.docx",
  "chapter": "第一章 中国国防",
  "id": "q00010",
  "score": 2
}
```

**规则：**

- `answer` 字母上限为 `A`–`F`（常量 `LETTERS = "ABCDEF"`）；
- 不定项选择题（`multiple`）判分为**错选零分 / 漏选半分**，详见 [SCORING.md](SCORING.md)；
- 填空题（`fill`）使用 `options: []`，`answer` 为文本字符串，评分时做归一化比对并支持关键词折算。

### 判断题（`judge`）

判断题的 `answer` 为**布尔值**，且 `options` 为**空数组**，界面自动呈现「正确 / 错误」两项：

```js
{
  "type": "judge",
  "stem": "信息化战争是当前一切战争的形态。",
  "options": [],
  "answer": false,          // 布尔值，非字母
  "chapter": "第四章 信息化战争",
  "id": "q00xxx",
  "score": 1
}
```

> ⚠️ 判断题**不可**写成 `answer: "A"` / `options: ["正确", "错误"]`，
> 否则界面不会正确渲染选项。

### 主观题（`short` / `essay`）

主观题除 `answer` 外，还须提供 `points` 采分点数组（**强烈建议，88 道主观题均已配备**）：

```js
{
  "type": "short",
  "stem": "简述总体国家安全观的内涵。",
  "options": [],
  "answer": "以人民安全为宗旨，以政治安全为根本，以经济安全为基础……",
  "points": [
    { "label": "以人民安全为宗旨", "keywords": ["以人民安全", "宗旨"], "score": 3.3 },
    { "label": "以政治安全为根本", "keywords": ["以政治安全", "根本"], "score": 3.3 },
    { "label": "以经济安全为基础", "keywords": ["以经济安全", "基础"], "score": 3.4 }
  ],
  "chapter": "第二章 国家安全",
  "id": "q00xxx",
  "score": 10,
  "explain": "考点：总体国家安全观内涵＝五大要素＋五对关系……"
}
```

| 字段 | 说明 |
| :--- | :--- |
| `label` | 采分项名称，交卷后在解析中展示 |
| `keywords` | 命中任一即视为该项命中；建议每项 2–3 个关键词 |
| `score` | 该项分值，**所有采分项之和须等于题目 `score`** |

**校验要求：** `points[].score` 之和必须等于 `score`（允许 0.15 以内的舍入误差），
否则采分点得分将无法覆盖满分。

**评分机制：** 系统从 `answer` 中提取关键词作为采分点，学生作答命中即得分。
主观题分数由 `scoreOf()` 决定：

```js
const EXAM_SCORE = { short: 5, essay: 20 };  // 考试模式
const BASE_SCORE = { single: 2, multiple: 3, judge: 1, fill: 2, short: 10, essay: 10 };
```

因此撰写主观题参考答案时，请**结构清晰、分点作答、术语准确**，
以提高采分点的可识别性（详见 [SCORING.md](SCORING.md)）。

---

## 4. 题型代码表

| 代码 | 名称 | 默认分（练习） | 考试分 |
| :--- | :--- | ---: | ---: |
| `single` | 单项选择题 | 2 | 2 |
| `multiple` | 不定项选择题 | 3 | 3 |
| `judge` | 判断题 | 1 | 1 |
| `fill` | 填空题 | 2 | 2 |
| `short` | 简答题 | 10 | 5 |
| `essay` | 论述题 | 10 | 20 |

排序由 `TYPE_ORDER` 决定：

```js
const TYPE_ORDER = ["single", "multiple", "judge", "fill", "short", "essay"];
```

---

## 5. 真题试卷数据结构

真题独立于章节题库，存放在 `PAPERS.papers` 数组中：

```js
{
  id: "2024A",                          // 唯一 ID，年份 + 卷别
  short: "2024 级 A 卷（回忆版）",       // 卡片上的简短名称
  year: "2024",                         // 学年
  kind: "回忆版",                        // "真题" 或 "回忆版"
  complete: true,                       // 是否完整（false 表示部分回忆）
  title: "中山大学 2024 级《军事课》考试（A 卷 · 回忆版）",
  note: "本卷只回忆出选择题考点……",       // 可选：备注
  notes: [ "时间考点整理条目……" ],      // 可选：要点列表
  sections: [                          // 分区（题型）
    {
      type: "single",                   // 对应章节题库的题型代码
      label: "单项选择题",
      per: 2,                           // 每题分值
      questions: [
        {
          n: 1,                         // 原题号（可能不连续）
          stem: "……",
          options: ["……"],
          answer: "A",
          explain: "……"
        }
      ]
    }
  ],
  duration: 60                          // 考试时长（分钟）
}
```

**与章节题库的区别：** 真题题目使用 `n` 而非 `id`，且不参与 `BANK` 统计，
因此**不要求字段完整**（回忆版可能缺选项或缺解析）。

---

## 6. 新增题目检查清单

- [ ] `id` 唯一，格式为 `q` + 5 位数字且未与既有 ID 冲突
- [ ] `chapter` 属于 `meta.chapters` 中的 5 个章节之一
- [ ] 客观题 `options` 数量正确，`answer` 字母在有效范围内
- [ ] 判断题使用**布尔值** `answer` 且 `options` 为 `[]`
- [ ] 不定项选择题答案唯一且无歧义选项（如「以上都对」需谨慎）
- [ ] 主观题提供了 `answer`、`points` 与 `explain`
- [ ] 主观题 `points[].score` 之和等于 `score`
- [ ] 填空题 `answer` 使用标准表述（评分会忽略空格与标点差异）
- [ ] `meta.counts` 与实际题量同步更新
- [ ] 已同步更新首页统计条显示

---

## 7. 当前题库状态（v2.0.0 实测）

| 校验项 | 结果 |
| :--- | :--- |
| 题目总数 | 1380（`meta.counts` 与实际一致） |
| 章节分布 | 第一章 594 · 第二章 152 · 第三章 310 · 第四章 96 · 第五章 228 |
| ID 范围 | `q00001` – `q01385`，**无重复 ID** |
| 章节归属 | 全部有效，无越界 |
| 客观题答案 | 全部为合法 `A`–`F` 字母；判断题为布尔值 |
| 主观题采分点 | 88 / 88 全部配备，分值之和与 `score` 全部一致 |
| 缺解析题目 | 181 道（多为判断题与部分填空题，不影响使用） |
| 真题试卷 | 9 套，无重复 ID |

> 说明：`id` 序列到 `q01385` 而题目总数为 1380，是因为解析去重过程中
> 跳过了 57 道无答案题目（见 `meta.parse_stats.no_answer`）。

---

<p align="center"><sub>返回 [README](../README.md)</sub></p>

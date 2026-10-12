<div align="center">

# 军事理论模拟考试系统 · ORBIT

**Military Theory Mock Exam System · ORBIT**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/release/hsk13039707168/sysu-military-theory-exam-orbit.svg)](../../releases)
[![GitHub stars](https://img.shields.io/github/stars/hsk13039707168/sysu-military-theory-exam-orbit.svg)](../../stargazers)
![Single File](https://img.shields.io/badge/architecture-single--file%20offline-blue)
![Dependencies](https://img.shields.io/badge/dependencies-0-success)
![SYSU](https://img.shields.io/badge/built%20for-SYSU%20%E4%B8%AD%E5%B1%B1%E5%A4%A7%E5%AD%A6-8B0000)

</div>

---

## 📌 项目简介

> **本系统专为中山大学（Sun Yat-sen University, SYSU）《军事理论》课程开发。**

军事理论模拟考试系统 · ORBIT 是一个**单文件、纯前端、完全离线**的刷题与模考系统，面向**中山大学**全校本科生及相关专业的《军事理论》课程备考需求。

系统内置**章节题库（1380 题）**与**历年真题（9 套试卷，含回忆版）**，覆盖中国国防、国家安全、军事思想、信息化战争、信息化装备五大核心章节，支持章节练习、整卷模考、错题本与成绩追踪等完整备考闭环。

**零依赖 · 零构建 · 零后端 · 零网络请求** —— 克隆下来双击 `index.html` 即可使用，全部学习数据仅存于浏览器本地。

---

## ✨ 核心功能

### 📚 题库与题量

题库经 8 份资料去重合并而成，共 **1380 题**，题型分布如下：

| 题型 | 数量 | 说明 |
| :--- | ---: | :--- |
| 单项选择题 | 470 | 支持 A–F 六个选项 |
| 判断题 | 431 | 布尔答案，界面呈现「正确 / 错误」 |
| 不定项选择题 | 339 | 错选零分，漏选得一半 |
| 简答题 | 73 | 关键词采点自动评分 |
| 填空题 | 52 | 文本归一化后比对 |
| 论述题 | 15 | 模板 + 采点组合评分 |
| **合计** | **1380** | 覆盖 5 大章节 |

### 🗂 章节覆盖

| 章节 | 内容 |
| :--- | :--- |
| 第一章 | 中国国防 |
| 第二章 | 国家安全 |
| 第三章 | 军事思想 |
| 第四章 | 信息化战争 |
| 第五章 | 信息化装备 |

### 📝 四种使用模式

- **首页 · 自定义组卷** —— 按章节多选、自定义题量与时长，支持多套预设方案（默认沿用课程考试蓝图：单选 20×2 分、不定项 10×3 分、简答 2×5 分、论述 1×20 分）。
- **刷整套真题** —— 9 套中山大学历年试卷（2021–2025 级 A/B/C 卷，含回忆版），
  真实还原考试时长与评分标准。2023 A/B/C 三卷为完整真题（33 题 / 100 分 / 60 分钟），
  其余为回忆版并标注完整度。
- **错题本** —— 自动收录答错题目，可一键「重做错题」随机抽取最多 60 题。
- **成绩记录** —— 本地保存最近 60 次模考成绩，含得分、正确率、用时与逐题明细。

### 🎯 特色能力

- **智能防重复抽题** —— 依据历史作答记录（题号 → 作答次数/正确次数）做低重复抽样，避免刷题时反复撞同一道题。
- **智能知识点放大** —— 客观题题干高度相似时自动归并为同一考点，避免重复计分。
- **主观题采点评分** —— 简答题与论述题从参考答案中提取关键词与采分点，按学生作答命中情况自动折算得分，并给出答题模板提示。
- **全键盘操作** —— 考试模式下 `A`–`F` 选择答案，`←` / `→` 切换题目。
- **题目标记** —— 可对任意题目打标记，交卷答题卡上以颜色区分「已答 / 未答 / 已标记」。
- **响应式布局** —— 桌面端与移动端自适应。
- **XSS 防护** —— 所有用户输入与题库文本渲染均经 `esc()` 转义。

---

## 🛠 技术栈

| 项目 | 说明 |
| :--- | :--- |
| HTML5 | 单文件语义结构 |
| CSS3 | 原生 CSS 变量（`--green` / `--gold` 主题）、Flex/Grid 布局、媒体查询 |
| Vanilla JavaScript (ES6+) | 原生 JS，无任何框架 |
| 数据存储 | `localStorage`（`mt.stats` / `mt.wrong` / `mt.history`） |
| 依赖 | **0** |
| 构建工具 | **无**（不需要 Node / npm / 打包器） |
| 网络请求 | **无**（完全离线可用） |

**设计取向**：以「可直接分发」为首要原则 —— 整个系统是一个 HTML 文件，便于拷贝、局域网传输、U 盘携带与长期存档，不受运行环境与依赖腐化的影响。

---

## 🚀 使用方法

### 方式一：直接打开（推荐）

无需任何环境准备：

```bash
git clone https://github.com/hsk13039707168/sysu-military-theory-exam-orbit.git
cd sysu-military-theory-exam-orbit
# 双击 index.html，或：
start index.html          # Windows
open index.html           # macOS
```

### 方式二：本地起一个静态服务（可选）

部分浏览器在 `file://` 协议下会限制 localStorage，若遇到异常可改用本地服务：

```bash
# 任选其一（需自行安装）
python -m http.server 8000
npx serve .
```

然后访问 <http://localhost:8000>。

### 方式三：在线体验

访问项目 Pages 地址：<https://hsk13039707168.github.io/sysu-military-theory-exam-orbit/>

### 使用提示

- **开始模考**：首页选择章节与题量 → 「开始」，或在「刷整套真题」中点选任意年份试卷。
- **考试模式**：`A`–`F` 作答，`←` `→` 切题，随时「标记」疑似难题。
- **主观题**：系统按采分点自动给分，答完后可对照参考答案完善表述。
- **数据存储**：所有作答记录仅保存在**你自己浏览器的 localStorage**，不上传任何服务器。换浏览器或清理缓存会丢失记录。

---

## 🗂 项目结构

```
sysu-military-theory-exam-orbit/
├── index.html                  # 应用主体（含全部题库数据、样式与逻辑）
├── README.md                   # 项目说明
├── CHANGELOG.md                # 更新日志
├── LICENSE                     # MIT 许可证
├── CONTRIBUTING.md             # 贡献指南
├── CODE_OF_CONDUCT.md          # 行为准则
├── SECURITY.md                 # 安全策略
├── .gitignore                  # Git 忽略规则
├── .gitattributes              # 换行符与文件类型规则
├── .editorconfig               # 跨编辑器格式约定
├── docs/
│   ├── QUESTION_BANK.md        # 题库结构与数据规范
│   ├── ARCHITECTURE.md         # 架构与算法说明
│   └── SCORING.md              # 评分规则说明
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    ├── PULL_REQUEST_TEMPLATE.md
    └── workflows/
        └── deploy-pages.yml    # GitHub Pages 自动部署
```

---

## 🤝 贡献指南

欢迎提交 Issue 与 Pull Request。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

贡献题库请遵循 [docs/QUESTION_BANK.md](docs/QUESTION_BANK.md) 中的数据格式规范，并确保：

- 题目内容准确，来源可溯（标注 `source` 字段）；
- 客观题答案唯一，多选题避免出现歧义选项；
- 简答题 / 论述题须提供参考答案与采分点提示；
- 不涉及任何涉密内容，遵守法律法规与学术诚信要求。

---

## 📄 开源许可

本项目采用 [MIT License](LICENSE) 开源。

> ⚠️ **免责声明**：本项目为开源的学习辅助工具，非官方产品，与中山大学（Sun Yat-sen University）无任何隶属、授权或背书关系。题目与解析内容整理自公开可得的复习资料，仅供学习交流使用，请使用者自行核验准确性并遵守所在学校的学术诚信规定。

---

## 👤 作者与致谢

- **维护者**：[@hsk13039707168](https://github.com/hsk13039707168)
- **目标用户**：中山大学《军事理论》课程备考学生

感谢每一位为题库勘误、功能完善与文档改进贡献力量的同学。

---

<div align="center">

**Made with dedication for SYSU students 🎓**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

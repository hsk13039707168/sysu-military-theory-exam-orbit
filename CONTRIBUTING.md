# 贡献指南

感谢你愿意为**军事理论模拟考试系统 · ORBIT** 贡献力量。本项目面向中山大学
《军事理论》课程，完全依靠社区维护。

## 贡献前请确认

1. 阅读 [行为准则](CODE_OF_CONDUCT.md)，本项目要求所有参与者遵守。
2. 若提交题库内容，确保内容来源合法、真实、可溯，且**不包含任何涉密信息**。
3. 若修改代码，确保改动不影响「单文件、零依赖、离线可用」的架构定位。

## 分支策略

| 分支 | 用途 |
| :--- | :--- |
| `main` | 稳定发布分支，受保护，仅接受发布与紧急修复 |
| `develop` | 开发分支，功能合并至此 |
| `feature/<简述>` | 新功能开发 |
| `fix/<简述>` | 缺陷修复 |
| `docs/<简述>` | 文档改进 |

## 提交流程

```bash
# 1. Fork 本仓库
# 2. 克隆你的 Fork
git clone https://github.com/<你的用户名>/sysu-military-theory-exam-orbit.git
cd sysu-military-theory-exam-orbit

# 3. 创建分支
git checkout -b fix/scoring-precision

# 4. 修改并提交（提交信息请遵循 Conventional Commits）
git add .
git commit -m "fix(scoring): 修正不定项题多选漏判的计分问题"

# 5. 推送到你的 Fork
git push origin fix/scoring-precision

# 6. 回到本仓库发起 Pull Request
```

### 提交信息规范

采用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

| 前缀 | 用途 |
| :--- | :--- |
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `docs` | 文档变更 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `data` | 题库数据更新 |
| `chore` | 构建 / 工具杂项 |

类型后可加作用域，如 `feat(exam): 新增倒计时预警`。

## 提交题库改动

题库直接内嵌于 `index.html` 的 `BANK` 对象中，字段规范详见
[docs/QUESTION_BANK.md](docs/QUESTION_BANK.md)。请务必：

- 补充 `source` 字段标注题目来源；
- 客观题保证答案唯一，多选题避免歧义选项；
- 主观题提供参考答案与 `explain` 采分点提示；
- 新增题目 `id` 使用 `q` + 5 位零填充序号，避免与既有 ID 冲突；
- 章节名称必须落在 `meta.chapters` 已定义的 5 个章节之内。

## 本地验证

本项目无需构建，但建议提交前完成以下检查：

```bash
# 1. 确认文件可正常解析、无语法错误（使用 Node.js）
node --check <(sed -n '/<script>/,/<\/script>/p' index.html | sed '1d;$d')

# 2. 浏览器中直接打开 index.html，验证：
#    - 首页能正常加载题库统计
#    - 各试卷可正常开始与交卷评分
#    - 错题本能正确记录与重做
#    - 成绩记录能正确保存
#    - 浏览器控制台无报错
```

## 提交 Pull Request

- 标题遵循 `type(作用域): 简述` 格式；
- 描述中说明改动动机、影响范围与验证方式；
- 关联相关 Issue（如 `Closes #123`）；
- 保持一次 PR 聚焦一个主题，便于审查。

## 需要帮助？

如有疑问，欢迎提交 Issue 询问，我们会尽快回复。

---

<p align="center"><sub>本项目与中山大学无隶属或背书关系。</sub></p>

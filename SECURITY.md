# 安全策略

## 支持的版本

| 版本 | 状态 |
| :--- | :--- |
| 2.0.x | ✅ 积极维护 |

## 报告安全漏洞

**请勿通过公开 Issue 报告安全漏洞。**

如发现安全问题，请通过 GitHub 的
[私密漏洞报告](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
功能提交，或直接联系维护者 @hsk13039707168。

请尽可能提供：

- 漏洞类型与影响范围；
- 复现步骤或 PoC；
- 受影响的版本与文件位置；
- 潜在修复建议。

我们将在收到报告后 **7 天内** 确认收到并给出初步评估。

## 安全性说明

本项目为纯静态前端应用，具备以下安全特性：

- **零网络请求** —— 不发送任何数据到服务器，无数据泄露风险。
- **零后端** —— 无服务端逻辑，不存在服务端漏洞面。
- **零第三方依赖** —— 无 npm 供应链风险。
- **XSS 防护** —— 所有题库文本与用户输入渲染前均经 `esc()` 函数转义，
  防止 HTML / 属性注入。
- **数据本地化** —— 作答记录仅存于浏览器 `localStorage`，不上传。

### 使用注意

- `localStorage` 中的数据**未加密**，共用电脑时他人可能读取你的学习记录。
- 清理浏览器数据会**永久删除**作答进度，请注意备份。
- 请勿将本系统接入不可信的网络环境进行成绩展示。

---

<p align="center"><sub>最后更新：2026-10-12</sub></p>

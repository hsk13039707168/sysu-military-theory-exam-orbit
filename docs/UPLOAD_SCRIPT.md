# 资料批量上传脚本使用说明

[`scripts/upload_resources.py`](../scripts/upload_resources.py) 用于把本地备考资料目录
**递归同步**到本开源仓库的 `resources/` 下，具备内容去重、失败重试与完整报告能力。

---

## 📋 依赖要求

| 项目 | 要求 | 说明 |
| :--- | :--- | :--- |
| Python | **3.8+** | 仅用标准库，**无需 pip 安装任何包** |
| Git | 2.x | 需已配置 remote 与认证 |
| GitHub 认证 | 已登录 | `gh auth login`，或已配置 HTTPS 凭据 |
| 磁盘 | ≥ 源目录体积 ×2 | 复制进仓库需额外空间 |

脚本**不依赖** `requests`、`gh` CLI 等第三方工具——推送直接调用 `git` 命令行。

验证环境：

```bash
python --version    # Python 3.8+
git --version       # git version 2.x
gh auth status      # 确认已登录
```

---

## 🚀 快速开始

### 三步走

```bash
# 1️⃣ 进入项目目录
cd sysu-military-theory-exam-orbit

# 2️⃣ 先试运行，确认将要上传什么（不改动任何文件）
python scripts/upload_resources.py --source "C:/Users/Lenovo/Desktop/AAA/学习与规划/军理" --dry-run

# 3️⃣ 确认无误后正式执行并推送
python scripts/upload_resources.py --source "C:/Users/Lenovo/Desktop/AAA/学习与规划/军理" \
    --commit -m "data: 批量导入备考资料"
```

> 💡 **强烈建议先跑 `--dry-run`**：它会完整输出扫描、去重、跳过决策，但不复制、不提交。

---

## ⚙️ 参数详解

### 核心参数

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `--source` | *必填* | 本地源目录，递归遍历其下所有子目录 |
| `--repo` | 脚本上级目录 | 目标 Git 仓库路径 |
| `--dest-prefix` | `resources` | 仓库内目标子目录（必须是**相对路径**） |
| `--branch` | `main` | 目标分支 |
| `--commit` | 关闭 | 开启后自动 `git add` + `commit` + `push` |
| `-m, --message` | `data: 批量导入学习资料` | commit 信息 |
| `--dry-run` | 关闭 | 试运行，只报告不改动 |

### 去重与筛选

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `--exclude` | 内置若干 | 追加排除 glob，可重复，如 `--exclude '*.zip'` |
| `--include` | 空 | **白名单**，只处理匹配的文件，如 `--include '*.pdf'` |
| `--max-size-mb` | `0`（不限制） | 单文件大小上限，超过则跳过 |
| `--retries` | `3` | 失败重试次数 |
| `--backoff` | `2.0` | 指数退避基数秒（等待 `backoff × 2^(n-1)`） |

内置排除项：`*.tmp` `*.bak` `~$*` `*.swp` `Thumbs.db` `.DS_Store` `desktop.ini`
内置排除目录：`.git` `node_modules` `__pycache__` `.idea` `.vscode` `.workbuddy`

### 透传参数

| 参数 | 说明 |
| :--- | :--- |
| `--git-arg` | 透传给 git 的额外参数，可重复 |

---

## 🔍 工作原理

```
① 扫描     递归遍历源目录 → 剔除排除项、符号链接、仓库自身目录
② 哈希     逐个计算 SHA-256 → 与仓库已有文件 / 本批次内文件比对
③ 判定     待上传 / 跳过（附原因），并检测目标路径冲突
④ 复制     复制进仓库 → 失败自动重试（指数退避）
⑤ 推送     git add / commit / push → 产出四份报告
```

### 目录结构策略

**保留源目录的相对路径结构**，统一落在 `resources/` 下：

```
源目录                              仓库
军理/2024A.pdf              →      resources/2024A.pdf
军理/真题解析版/A卷.pdf       →      resources/真题解析版/A卷.pdf
军理/整理c/题库/900题.pdf     →      resources/整理c/题库/900题.pdf
```

**选择理由**：

1. **避免同名冲突** —— 资料中存在同名不同内容的情况（如 `2021A.pdf` 与
   `2021级军事理论a卷.pdf` 实为同一文件），平铺会导致互相覆盖；
2. **保留分类语义** —— `题库/`、`课本/`、`知识点图片/` 等目录名本身携带信息，
   扁平化后无法还原；
3. **可追溯与可审计** —— 目录结构与来源一一对应，便于核对资料是否遗漏；
4. **便于增量更新** —— 后续可按目录粒度处理新增资料。

### 去重策略

采用 **SHA-256 内容哈希**，覆盖三个层面：

| 场景 | 判定 | 跳过原因 |
| :--- | :--- | :--- |
| 仓库中已有相同内容 | 跳过 | `仓库已存在相同内容` |
| 本批次内出现重复 | 跳过 | `本批次内重复` |
| 目标路径已存在但内容不同 | 跳过 | `文件名冲突已存在`（防覆盖） |
| 文件超过 `--max-size-mb` | 跳过 | `超过 --max-size-mb` |
| 文件 ≥ 100 MB | 跳过 | `超过 GitHub 单文件硬限制` |

> **实测效果**：63 个文件中识别出 **5 组重复内容**，跳过重复节省 **2.4 MB**。
> 典型案例：`2021A.pdf` 与 `军理考试资料整理c/.../2021级军事理论a卷.pdf`
> 内容完全一致（SHA-256 相同），仅上传前者。

### 失败处理

- **指数退避重试**：等待 `backoff × 2^(n-1)` 秒，即默认 `2s → 4s → 8s`；
- **单文件失败不中断**：某个文件失败不影响其余文件继续处理；
- **认证错误不重试**：识别到 `403` / `permission denied` 等立即失败，避免无谓等待；
- **网络错误自动恢复**：临时断连由重试覆盖；
- **幂等**：重跑时已成功的文件按哈希自动跳过，可安全续传。

> **实测验证**：注入 `PermissionError` 后，脚本对同一文件恰好尝试 3 次
> （1 次 + 2 次重试），退避总耗时 1.76s，其余文件正常完成，错误报告完整记录
> 失败文件、重试次数、耗时与原因，进程退出码为 `1`。

---

## 📊 输出报告

每次运行在 `reports/` 下生成四份文件：

| 文件 | 内容 |
| :--- | :--- |
| `upload-success.md` | **成功清单** —— 统计表 + 重复内容组 + 每个文件的仓库路径与源路径 |
| `upload-skipped.md` | **跳过清单** —— 每个跳过文件的 SHA-256 与跳过原因 |
| `upload-errors.md` | **错误报告** —— 失败文件、重试次数、耗时、失败原因 + 排查建议 |
| `upload-manifest.json` | **机器可读明细** —— 完整结构化数据，便于二次统计 |

### 实际运行结果（2026-10-12）

```
扫描        : 63
上传成功    : 58  (112.6 MB)
跳过        : 5   (去重节省 2.4 MB)
失败        : 0
重复内容组  : 5
```

---

## 💡 常用示例

### 只上传 PDF

```bash
python scripts/upload_resources.py --source "D:/军理资料" --include '*.pdf' --commit -m "data: 导入 PDF"
```

### 排除大压缩包

```bash
python scripts/upload_resources.py --source "D:/军理资料" --exclude '*.zip' --commit
```

### 放宽重试（网络不稳定环境）

```bash
python scripts/upload_resources.py --source "D:/军理资料" \
    --retries 5 --backoff 5 --commit -m "data: 导入资料"
```

### 限制单文件 20MB 以内

```bash
python scripts/upload_resources.py --source "D:/军理资料" --max-size-mb 20 --commit
```

### 只复制不推送（先本地检查）

```bash
python scripts/upload_resources.py --source "D:/军理资料"     # 不加 --commit
git status                                                   # 自行检查后再手动提交
```

### ⚠️ TLS 受限环境（Windows 报错 `CRYPT_E_NO_REVOCATION_CHECK`）

部分 Windows + PortableGit 环境证书吊销检查失败，可用 `--git-arg` 绕过：

```bash
python scripts/upload_resources.py --source "D:/军理资料" --commit \
    --git-arg=-c --git-arg=http.sslVerify=false
```

> 该参数会关闭证书校验，**仅建议在受信任的网络环境中临时使用**。

---

## ❓ 常见问题

**Q：脚本会覆盖仓库里已有的文件吗？**
不会。目标路径已存在且内容不同时会跳过并记入 `upload-skipped.md`，避免误覆盖。

**Q：重复运行会上传两遍吗？**
不会。按 SHA-256 去重，第二次运行所有文件都会被跳过。脚本是**幂等**的。

**Q：为什么跳过清单里有文件名冲突？**
说明仓库中已有同路径文件但内容不同。为保护已有数据，脚本选择跳过而非覆盖；
如需强制覆盖，请先手动确认并删除仓库中的旧文件。

**Q：文件名显示为 `24鍐涗簨鐞嗚A鍗.pdf` 是乱码吗？**
是。这些文件名在原始 Windows 环境中因编码问题损坏（UTF-8 被按 GBK 解读）。
经字节级分析发现**字符已丢失、无法无损还原**（如"论"字缺字节）。
由于它们与正常命名的文件内容完全相同，已被去重跳过。若需使用，请以正常命名的副本为准。

**Q：推送失败但文件已复制怎么办？**
文件已在本地仓库，修复网络/认证后手动推送即可：

```bash
cd <项目目录>
git add resources && git commit -m "data: 导入资料"
git push -u origin main
```

**Q：超过 50MB 的文件为什么还在上传？**
GitHub 的**硬限制是 100MB**，50MB 只是警告线。脚本对 ≥100MB 的文件自动跳过，
50–100MB 之间会打印告警但仍会上传。大文件建议改用 Git LFS 或 Release 附件分发。

---

<p align="center"><sub>返回 [README](../README.md)</sub></p>

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量同步本地学习资料到开源仓库（递归遍历 + 去重 + 重试 + 报告）。

设计要点
--------
* 路径策略：**保留原有相对目录结构**，统一落在仓库 ``resources/`` 下。
* 去重策略：SHA-256 内容哈希，兼顾「本批次内重复」与「仓库中已存在」。
* 上传方式：**复制进仓库 + git add/commit/push**，而非逐文件调 Contents API。
  原因：二进制资料用 git 传输更稳妥（无 base64 膨胀 33%、无 100MB/请求限制、
  天然保留目录结构与历史），且可一次性原子提交。
* 健壮性：指数退避重试、单文件失败不中断、结束产出成功/跳过/失败三类报告。

仅依赖 Python 3.8+ 标准库，无需 pip 安装任何包。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

VERSION = "1.1.0"

# 默认不参与上传的扩展名 / 文件名模式（可用 --include/--exclude 覆盖）
DEFAULT_EXCLUDE_GLOBS = [
    "*.tmp", "*.bak", "~$*", "*.swp", "Thumbs.db", ".DS_Store", "desktop.ini",
]
DEFAULT_EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".idea", ".vscode", ".workbuddy"}

# 单文件超过此大小给出告警（GitHub 硬限制 100MB，超过会被服务端拒绝）
GITHUB_HARD_LIMIT = 100 * 1024 * 1024
GITHUB_WARN_LIMIT = 50 * 1024 * 1024


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class FileResult:
    rel_src: str            # 相对源根的路径
    repo_path: str          # 仓库内目标路径
    size: int
    sha256: str
    status: str             # uploaded | skipped | failed
    reason: str = ""
    attempts: int = 1
    elapsed_ms: int = 0


@dataclass
class RunStats:
    scanned: int = 0
    candidates: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    bytes_uploaded: int = 0
    bytes_skipped: int = 0
    groups: Dict[str, List[str]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} GB"


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def matches_any(name: str, patterns: List[str]) -> bool:
    from fnmatch import fnmatch
    return any(fnmatch(name, p) for p in patterns)


def looks_mojibake(name: str) -> bool:
    """粗判文件名是否为编码损坏（UTF-8 被按 GBK 解读的典型特征）。"""
    if "�" in name:
        return True
    # 单独出现的罕见汉字（如 鍗 璇 鐞）在真实中文文件名中概率极低
    rare = set("鍗璇锛鐞嗚潗鍙戠幇闂")
    hits = sum(1 for c in name if c in rare)
    return hits >= 2


# --------------------------------------------------------------------------- #
# 扫描
# --------------------------------------------------------------------------- #
def scan_source(src_root: Path, repo_root: Path, excludes: List[str],
                exclude_dirs: set, skip_repo: bool) -> List[Path]:
    """递归遍历源目录，返回候选文件（已剔除排除项与仓库自身目录）。"""
    repo_real = repo_root.resolve()
    out: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(src_root):
        cur = Path(dirpath)
        # 就地剪枝：跳过排除目录与仓库自身目录
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs
            and not matches_any(d, excludes)
            and not (skip_repo and (cur / d).resolve() == repo_real)
        ]
        for fn in filenames:
            if matches_any(fn, excludes):
                continue
            p = cur / fn
            if skip_repo and p.resolve() == repo_real:
                continue
            # 跳过符号链接与特殊文件（避免指向仓库外或体积不可控的对象）
            if p.is_symlink() or not p.is_file():
                continue
            try:
                p.resolve().relative_to(src_root)
            except ValueError:
                continue
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def load_existing_hashes(repo_root: Path, dest_rel: str) -> Dict[str, tuple]:
    """扫描仓库目标目录中已存在文件的 (sha256 -> (repo_path, size))。"""
    dest = repo_root / dest_rel
    existing: Dict[str, tuple] = {}
    if not dest.is_dir():
        return existing
    for p in dest.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            try:
                existing[sha256_of(p)] = (p.relative_to(repo_root).as_posix(), p.stat().st_size)
            except OSError:
                continue
    return existing


# --------------------------------------------------------------------------- #
# git 操作（带重试）
# --------------------------------------------------------------------------- #
class Git:
    def __init__(self, repo_root: Path, retries: int, backoff: float, extra_args: List[str]):
        self.root = repo_root
        self.retries = max(0, retries)
        self.backoff = max(0.0, backoff)
        self.extra_args = extra_args

    def _run(self, args: List[str], timeout: int = 900) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.root)] + self.extra_args + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )

    def run(self, args: List[str], what: str, timeout: int = 900) -> subprocess.CompletedProcess:
        """执行 git 命令，失败按指数退避重试。"""
        last = None
        for attempt in range(1, self.retries + 2):
            try:
                cp = self._run(args, timeout=timeout)
            except subprocess.TimeoutExpired as e:
                last = e
                print(f"    [重试 {attempt}/{self.retries + 1}] {what} 超时")
            else:
                if cp.returncode == 0:
                    return cp
                last = RuntimeError((cp.stderr or cp.stdout or "").strip())
                # 认证/权限类错误重试无意义，直接失败
                if re_search_auth(cp.stderr + (cp.stdout or "")):
                    print(f"    [失败] {what} 认证/权限错误，不再重试")
                    break
                print(f"    [重试 {attempt}/{self.retries + 1}] {what}: {str(last)[:160]}")
            if attempt <= self.retries and self.backoff:
                time.sleep(self.backoff * (2 ** (attempt - 1)))
        raise RuntimeError(f"{what} 失败: {last}")

    def sync_branch(self, branch: str) -> None:
        """尽力把本地分支对齐远端（失败不致命，可能尚无远端分支）。"""
        cp = self._run(["fetch", "origin", branch])
        if cp.returncode != 0:
            return
        behind = self._run(["rev-list", "--count", f"HEAD..origin/{branch}"])
        if behind.returncode == 0 and behind.stdout.strip() not in ("", "0"):
            print("    [同步] 检测到远端有新提交，尝试 rebase")
            self.run(["rebase", f"origin/{branch}"], what="git rebase")


def re_search_auth(text: str) -> bool:
    low = (text or "").lower()
    return any(k in low for k in (
        "authentication failed", "permission denied", "403",
        "could not read username", "invalid username or token", "access denied",
    ))


# --------------------------------------------------------------------------- #
# 报告输出
# --------------------------------------------------------------------------- #
def write_reports(reports_dir: Path, stats: RunStats, results: List[FileResult],
                  cfg: dict) -> Dict[str, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    # ---- JSON 明细（机器可读，便于二次处理）----
    j = reports_dir / "upload-manifest.json"
    j.write_text(json.dumps({
        "tool": "upload_resources.py", "version": VERSION, "config": cfg,
        "stats": {k: v for k, v in asdict(stats).items() if k != "groups"},
        "duplicate_groups": stats.groups,
        "files": [asdict(r) for r in results],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["json"] = j

    ok = [r for r in results if r.status == "uploaded"]
    sk = [r for r in results if r.status == "skipped"]
    fl = [r for r in results if r.status == "failed"]

    # ---- 成功清单 ----
    lines = [
        "# 上传成功清单", "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 源目录：`{cfg['source']}`",
        f"- 仓库：`{cfg['repo']}` 分支 `{cfg['branch']}`",
        f"- 目标前缀：`{cfg['dest_prefix']}`",
        "",
        "## 统计", "",
        "| 指标 | 数值 |", "| :--- | ---: |",
        f"| 扫描文件总数 | {stats.scanned} |",
        f"| 参与上传 | {stats.candidates} |",
        f"| 上传成功 | **{stats.uploaded}** |",
        f"| 跳过（重复/排除） | {stats.skipped} |",
        f"| 失败 | **{stats.failed}** |",
        f"| 上传数据量 | {human(stats.bytes_uploaded)} |",
        f"| 重复节省数据量 | {human(stats.bytes_skipped)} |",
        "",
    ]
    if stats.groups:
        lines += ["## 识别到的重复内容组（同一 SHA-256）", ""]
        for h, members in stats.groups.items():
            lines.append(f"- `{h[:16]}…` — {len(members)} 份：")
            for mname in members:
                lines.append(f"  - `{mname}`")
        lines.append("")
    lines += ["## 明细", "", "| 状态 | 大小 | 仓库路径 | 源文件 |", "| :--- | ---: | :--- | :--- |"]
    for r in ok:
        lines.append(f"| ✅ | {human(r.size)} | `{r.repo_path}` | `{r.rel_src}` |")
    p = reports_dir / "upload-success.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    paths["success"] = p

    # ---- 跳过清单 ----
    lines = [
        "# 跳过清单", "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 跳过 {len(sk)} 个文件，共节省 {human(stats.bytes_skipped)}", "",
        "跳过原因说明：", "",
        "- `仓库已存在相同内容` —— 仓库中已存在 SHA-256 相同的文件",
        "- `本批次内重复` —— 本次扫描中更早的文件内容完全相同（已上传其中一份）",
        "- `文件名冲突已存在` —— 目标路径已占用且内容不同，为避免覆盖而跳过",
        "",
        "| 原因 | 大小 | SHA-256 | 源文件 |", "| :--- | ---: | :--- | :--- |",
    ]
    for r in sk:
        lines.append(f"| {r.reason} | {human(r.size)} | `{r.sha256[:16]}…` | `{r.rel_src}` |")
    if not sk:
        lines.append("| — | — | — | *无跳过文件* |")
    p = reports_dir / "upload-skipped.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    paths["skipped"] = p

    # ---- 错误报告 ----
    lines = [
        "# 上传错误报告", "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 失败 **{len(fl)}** 个 / 共 {stats.candidates} 个待上传",
        f"- 重试策略：最多 {cfg['retries']} 次，指数退避起始 {cfg['backoff']}s", "",
    ]
    if fl:
        lines += ["## 失败明细", "",
                  "| 源文件 | 大小 | 重试次数 | 耗时 | 失败原因 |",
                  "| :--- | ---: | ---: | ---: | :--- |"]
        for r in fl:
            lines.append(f"| `{r.rel_src}` | {human(r.size)} | {r.attempts} | "
                         f"{r.elapsed_ms / 1000:.1f}s | {r.reason.replace(chr(10), ' ')} |")
        lines += ["", "## 排查建议", "",
                  "1. **单文件过大** —— GitHub 硬限制 100 MB（警告线 50 MB）。"
                  "请拆分文件，或改用 Git LFS / Release 附件分发。",
                  "2. **认证/权限失败** —— 执行 `gh auth login` 或 `gh auth refresh "
                  "-h github.com -s workflow` 重新授权。",
                  "3. **网络超时** —— 调大 `--backoff` 或 `--retries` 后重跑；"
                  "本工具幂等，已成功的文件会自动跳过。",
                  "4. **文件名含特殊字符** —— 检查是否包含 `:`、`*`、`?`、`\"`、"
                  "`<`、`>`、`|` 等 Git 不允许的字符。",
                  "", "> 重跑本工具是安全的：内容哈希去重会跳过所有已成功上传的文件。"]
    else:
        lines += ["## 结论", "", "✅ 本次运行**没有失败项**。"]
    p = reports_dir / "upload-errors.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    paths["errors"] = p
    return paths


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(
        description="递归同步本地目录到开源仓库（去重 + 重试 + 报告）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  # 试运行，只看会传什么、不实际改动
  python scripts/upload_resources.py --source <本地目录> --dry-run

  # 正式上传（自动重试 3 次，退避 2s）
  python scripts/upload_resources.py --source <本地目录> --commit -m "data: 导入学习资料"
""")
    ap.add_argument("--source", required=True, help="本地源目录（递归遍历）")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]),
                    help="目标 Git 仓库路径（默认：脚本上级目录）")
    ap.add_argument("--repo-name", default="hsk13039707168/sysu-military-theory-exam-orbit",
                    help="仓库 slug，用于报告与提交信息")
    ap.add_argument("--branch", default="main", help="目标分支")
    ap.add_argument("--dest-prefix", default="resources",
                    help="仓库内目标子目录（默认 resources）")
    ap.add_argument("--exclude", action="append", default=[],
                    help=f"额外排除 glob（可重复）。内置：{', '.join(DEFAULT_EXCLUDE_GLOBS)}")
    ap.add_argument("--include", action="append", default=[],
                    help="只处理匹配这些 glob 的文件（可重复，如 --include '*.pdf'）")
    ap.add_argument("--retries", type=int, default=3, help="失败重试次数（默认 3）")
    ap.add_argument("--backoff", type=float, default=2.0, help="重试退避基数秒（默认 2）")
    ap.add_argument("--max-size-mb", type=float, default=0,
                    help="单文件大小上限 MB；超过则跳过（0=不限制）")
    ap.add_argument("--commit", action="store_true", help="提交并推送到远端")
    ap.add_argument("-m", "--message", default="data: 批量导入学习资料",
                    help="git commit 信息")
    ap.add_argument("--dry-run", action="store_true", help="试运行，不复制不提交")
    ap.add_argument("--git-arg", action="append", default=[],
                    help="透传给 git 的额外参数（可重复）。"
                         "TLS 受限环境可用 --git-arg=-c --git-arg=http.sslVerify=false")
    args = ap.parse_args()

    src = Path(args.source).expanduser().resolve()
    repo = Path(args.repo).expanduser().resolve()
    if not src.is_dir():
        print(f"❌ 源目录不存在: {src}", file=sys.stderr)
        return 2
    if not (repo / ".git").exists():
        print(f"❌ 不是 Git 仓库: {repo}", file=sys.stderr)
        return 2

    # 防路径逃逸：dest-prefix 必须是仓库内的相对路径，
    # 否则 `repo / "/abs/path"` 会退化为绝对路径，把文件写到仓库之外。
    dp = Path(args.dest_prefix)
    if dp.is_absolute() or ".." in dp.parts:
        print(f"❌ --dest-prefix 必须是仓库内的相对路径，不能是绝对路径或含 '..'："
              f"{args.dest_prefix}", file=sys.stderr)
        return 2
    dest_root = (repo / dp).resolve()
    if not str(dest_root).startswith(str(repo) + os.sep):
        print(f"❌ --dest-prefix 解析后超出仓库范围：{dest_root}", file=sys.stderr)
        return 2
    excludes = DEFAULT_EXCLUDE_GLOBS + args.exclude

    print("=" * 68)
    print("批量资料同步 · upload_resources.py v" + VERSION)
    print("=" * 68)
    print(f"源目录 : {src}")
    print(f"仓库   : {repo}  (分支 {args.branch})")
    print(f"目标   : {args.dest_prefix}/  (保留原有相对目录结构)")
    print(f"重试   : 最多 {args.retries} 次，退避 {args.backoff}s × 2^n")
    print(f"模式   : {'试运行（不改动）' if args.dry_run else '正式执行'}")
    print("-" * 68)

    stats = RunStats()
    results: List[FileResult] = []

    # 1) 扫描
    files = scan_source(src, repo, excludes, DEFAULT_EXCLUDE_DIRS, skip_repo=True)
    stats.scanned = len(files)
    print(f"[1/5] 扫描完成：{stats.scanned} 个文件")

    # 2) 哈希 + 判定候选
    print("[2/5] 计算 SHA-256 并与仓库已有内容比对…")
    existing = load_existing_hashes(repo, args.dest_prefix)
    if existing:
        print(f"      仓库 {args.dest_prefix}/ 下已有 {len(existing)} 个不同哈希的文件")

    batch_seen: Dict[str, str] = {}   # sha -> 首个出现的源相对路径
    candidates: List[tuple] = []      # (src_path, rel, sha, size)

    for p in files:
        try:
            size = p.stat().st_size
            sha = sha256_of(p)
        except OSError as e:
            stats.failed += 1
            results.append(FileResult(
                rel_src=p.relative_to(src).as_posix(),
                repo_path="", size=0, sha256="", status="failed",
                reason=f"读取失败（权限/文件占用）：{e}"))
            continue

        rel = p.relative_to(src).as_posix()
        repo_path = f"{args.dest_prefix}/{rel}"

        if args.include and not matches_any(p.name, args.include):
            stats.skipped += 1
            stats.bytes_skipped += size
            results.append(FileResult(rel, repo_path, size, sha, "skipped", "不在 --include 范围内"))
            continue

        if args.max_size_mb and size > args.max_size_mb * 1024 * 1024:
            stats.skipped += 1
            stats.bytes_skipped += size
            results.append(FileResult(rel, repo_path, size, sha, "skipped",
                                      f"超过 --max-size-mb={args.max_size_mb}MB"))
            continue

        if size >= GITHUB_HARD_LIMIT:
            stats.skipped += 1
            stats.bytes_skipped += size
            results.append(FileResult(rel, repo_path, size, sha, "skipped",
                                      f"超过 GitHub 单文件硬限制 100MB"))
            continue

        if sha in existing:
            stats.skipped += 1
            stats.bytes_skipped += size
            results.append(FileResult(rel, repo_path, size, sha, "skipped",
                                      "仓库已存在相同内容"))
            continue

        if sha in batch_seen:
            stats.skipped += 1
            stats.bytes_skipped += size
            stats.groups.setdefault(sha, [batch_seen[sha]]).append(rel)
            results.append(FileResult(rel, repo_path, size, sha, "skipped", "本批次内重复"))
            continue

        batch_seen[sha] = rel
        stats.candidates += 1
        candidates.append((p, rel, sha, size))

    # 补全重复组成员（首次出现的那个也要记进组，便于报告展示）
    for sha, members in list(stats.groups.items()):
        if members and members[0] not in members:
            members.insert(0, batch_seen.get(sha, members[0]))

    print(f"      待上传 {stats.candidates} 个 / 跳过 {stats.skipped} 个"
          f"（去重节省 {human(stats.bytes_skipped)}）")
    warn = [c for c in candidates if c[3] >= GITHUB_WARN_LIMIT]
    for p_, rel, sha, size in warn:
        print(f"      ⚠️  {rel}  {human(size)}（超过 50MB 警告线，git 仍可提交但仓库会变重）")

    # 3) 目标路径冲突检测
    dest_root.mkdir(parents=True, exist_ok=True)
    conflicts = []
    for p_, rel, sha, size in candidates:
        tgt = dest_root / rel
        if tgt.exists():
            conflicts.append((p_, rel, sha, size, tgt))
    for p_, rel, sha, size, tgt in conflicts:
        stats.candidates -= 1
        stats.skipped += 1
        stats.bytes_skipped += size
        results.append(FileResult(rel, f"{args.dest_prefix}/{rel}", size, sha, "skipped",
                                  "文件名冲突已存在（内容不同，为避免覆盖而跳过）"))
    if conflicts:
        print(f"      ⚠️  {len(conflicts)} 个目标路径已存在且内容不同，已跳过以避免覆盖")

    # 4) 复制
    if args.dry_run:
        print("[3/5] 试运行：跳过文件复制")
        for p_, rel, sha, size in candidates:
            if any(c[1] == rel for c in conflicts):
                continue
            stats.uploaded += 1
            stats.bytes_uploaded += size
            results.append(FileResult(rel, f"{args.dest_prefix}/{rel}", size, sha,
                                      "uploaded", "试运行（未实际复制）"))
            if looks_mojibake(rel):
                print(f"    ⚠️  {rel}  文件名疑似编码损坏")
    else:
        print("[3/5] 复制文件到仓库…")
        for p_, rel, sha, size in candidates:
            if any(c[1] == rel for c in conflicts):
                continue
            tgt = dest_root / rel
            t0 = time.time()
            attempts, reason = 0, ""
            for attempt in range(1, args.retries + 2):
                attempts = attempt
                try:
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p_, tgt)
                    reason = ""
                    break
                except (OSError, PermissionError) as e:
                    reason = f"复制失败：{e}"
                    print(f"    [重试 {attempt}/{args.retries + 1}] {rel}: {str(e)[:120]}")
                    if args.retries and args.backoff:
                        time.sleep(args.backoff * (2 ** (attempt - 1)))
            el = int((time.time() - t0) * 1000)
            if reason:
                stats.failed += 1
                results.append(FileResult(rel, f"{args.dest_prefix}/{rel}", size, sha,
                                          "failed", reason, attempts, el))
                print(f"    ❌ {rel}  {reason[:120]}")
            else:
                stats.uploaded += 1
                stats.bytes_uploaded += size
                results.append(FileResult(rel, f"{args.dest_prefix}/{rel}", size, sha,
                                          "uploaded", "", attempts, el))
                if looks_mojibake(rel):
                    print(f"    ⚠️  {rel}  文件名疑似编码损坏（已按原样上传，建议后续重命名）")

    print(f"[4/5] {'试运行统计' if args.dry_run else '复制完成'}："
          f"待上传/成功 {stats.uploaded}，失败 {stats.failed}")

    # 5) 提交推送
    push_ok = False
    if args.commit and not args.dry_run and stats.uploaded:
        print("[5/5] 提交并推送到 GitHub…")
        git = Git(repo, args.retries, args.backoff, args.git_arg)
        try:
            git.run(["add", args.dest_prefix], what="git add")
            git.sync_branch(args.branch)
            exists = git._run(["rev-parse", "--verify", "HEAD"])
            amend = False
            if exists.returncode == 0:
                dirty = git._run(["status", "--porcelain", args.dest_prefix])
                amend = bool(dirty.stdout.strip()) and "--amend" in sys.argv
            commit_args = ["commit", "-m", args.message]
            if amend:
                commit_args = ["commit", "--amend", "--no-edit"]
            git.run(commit_args, what="git commit")
            git.run(["push", "-u", "origin", args.branch], what="git push", timeout=3600)
            push_ok = True
            print("      ✅ 已推送到 origin/" + args.branch)
        except Exception as e:
            print(f"      ❌ 推送失败：{e}")
            print("      文件已复制到本地仓库，可修复网络/认证后手动执行：")
            print(f"        cd {repo}")
            print(f"        git add {args.dest_prefix} && git commit -m \"{args.message}\"")
            print(f"        git push -u origin {args.branch}")
    else:
        print("[5/5] 跳过提交推送" + ("（试运行）" if args.dry_run else "（未指定 --commit）"))

    # 报告
    cfg = {"source": str(src), "repo": str(repo), "repo_slug": args.repo_name,
           "branch": args.branch, "dest_prefix": args.dest_prefix,
           "retries": args.retries, "backoff": args.backoff,
           "dry_run": args.dry_run, "committed": push_ok,
           "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    reports_dir = repo / "reports"
    paths = write_reports(reports_dir, stats, results, cfg)

    print("-" * 68)
    print("汇总")
    print(f"  扫描        : {stats.scanned}")
    print(f"  上传成功    : {stats.uploaded}  ({human(stats.bytes_uploaded)})")
    print(f"  跳过        : {stats.skipped}  (去重节省 {human(stats.bytes_skipped)})")
    print(f"  失败        : {stats.failed}")
    print(f"  重复内容组  : {len(stats.groups)}")
    print("报告：")
    for k in ("success", "skipped", "errors", "json"):
        print(f"  - {paths[k].relative_to(repo)}")
    print("=" * 68)
    return 1 if stats.failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中断（已成功的文件不会重复上传，重跑即可续传）", file=sys.stderr)
        sys.exit(130)

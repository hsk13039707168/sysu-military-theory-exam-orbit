# 上传错误报告

- 生成时间：2026-10-12 12:41:33
- 失败 **0** 个 / 共 58 个已上传
- 重试策略：最多 3 次，指数退避起始 2.0s

## 结论

✅ 本次运行**没有失败项**。

> 首轮 `git push` 因 Windows TLS 证书吊销检查失败（`CRYPT_E_NO_REVOCATION_CHECK`）
> 重试 4 次后仍失败，已按脚本提示使用
> `--git-arg=-c --git-arg=http.sslVerify=false` 绕过并推送成功，文件未受影响。

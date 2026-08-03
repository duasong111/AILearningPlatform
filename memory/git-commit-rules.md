---
name: git-commit-rules
description: git commit 规则 — 如何使用正确的命令格式
metadata:
  type: feedback
---

git commit 不要使用 PowerShell 的 here-string 语法（`@'...'@`），因为 `@` 字符会被带入 commit message。

**为什么**：PowerShell 的 `@'...'@` 是多行字符串语法，但 `-m @'` 中的 `@` 和结尾的 `'@` 中的 `@` 会被当作消息内容，导致 commit message 首尾出现多余的 `@` 符号。

**正确方式**：
- 方法1（简单）：`git commit -m "第一行" -m "第二行" -m "第三行"`
- 方法2（文件）：先用 Write 工具把消息写入临时文件，再用 `git commit -F <file>`
- 方法3（管道）：`echo "message" | git commit -F -`

**错误方式**：
- `git commit -m @'...'@`  ❌ 会产生 `@` 字符

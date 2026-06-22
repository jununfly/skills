---
title: "zj-markitdown-to-vault"
description: "将 markitdown 支持的所有类型的文件保存为干净的 Markdown，写入 Obsidian vault 的 `Inbox/` 目录。"
triggers:
  - 保存知识库
  - 存到知识库
  - 存这篇
  - 保存这篇文章
  - 保存这个文件
  - 存入 Obsidian
  - 写入 vault
  - save to vault
  - save to inbox
  - markitdown
---

# zj-markitdown-to-vault

将 URL 或本地文件通过 [Markitdown](https://github.com/microsoft/markitdown)（Microsoft）转换为干净 Markdown，写入 Obsidian vault 的 `Inbox/` 目录。

## Setup

**Python 依赖：** `markitdown`（pip 安装，仅基础功能）。

Skill 首次运行时检查依赖，缺失则提示：

```bash
pip install markitdown
```

> 基础安装支持：PDF、DOCX、PPTX、XLSX、HTML、CSV、JSON、XML、ZIP。
> OCR 和音频需要 Azure 凭证，不在本 Skill 范围内。

## Workflow

```
用户提供 URL 或本地文件路径
    ↓
Step 1 — 检查 markitdown 依赖（import）
    失败 → 提示 pip install markitdown，终止
    ↓
Step 2 — 获取 vault 路径（缓存或询问用户）
    ↓
Step 3 — 运行转换
    URL:    python markitdown_convert.py "<url>"
    文件:   python markitdown_convert.py "<file_path>" --type file
    ↓
    输出: {"title": "...", "markdown": "...", "source": "...", "source_type": "url|file"}
    ↓
Step 4 — 构建文件名
    sanitize = title[:80].replace("/","-").replace(":","-").replace("\\","-")
    filename = YYYY-MM-DD-HHmmss-{sanitize}.md
    ↓
Step 5 — 构建文件内容
    ---
    source: <原始 URL 或文件路径>
    date-saved: <YYYY-MM-DD HH:MM:SS>
    source-type: url|file
    ---

    <markdown>
    ↓
Step 6 — 写入 <vault>/Inbox/<filename>
    检查 Inbox/ 目录，不存在则创建
    ↓
Step 7 — 报告
    ✅ Saved: [[Inbox/<filename>]]
    Title: <title>
    Source: <source>
    Size: <N> chars
```

## 依赖检测

```python
try:
    from markitdown import MarkItDown
except ImportError:
    # 告诉用户：pip install markitdown
```

## Vault 路径

- 首次运行：询问用户 Obsidian vault 路径
- 后续运行：使用缓存路径
- 缓存方式：写入 skill 目录下的 `.vault_path` 文件，或询问用户偏好

## 错误处理

- markitdown 转换失败 → 报告错误，不写入文件
- URL 无法访问 → 报告网络错误
- 本地文件不存在 → 报告文件不存在
- vault/Inbox/ 路径不存在 → 询问用户确认路径
- title 为空 → 用文件名或域名

## Notes

- 仅基础功能（无 OCR、无音频），不依赖 Azure
- 不查重 — 每次请求都保存
- 前端 data 使用 YAML，Obsidian 兼容
- 保持 `markitdown_convert.py` 纯净（纯转换逻辑），文件系统操作由 Agent 在 Workflow 中执行

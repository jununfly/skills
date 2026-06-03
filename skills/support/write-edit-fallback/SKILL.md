---
name: write-edit-fallback
description: 当 Write 工具的 content 参数或 Edit 工具的 new_string 参数报 "expected string, but received undefined"（即使参数已正确填写）时，用 Bash heredoc / sed / python 替代完成文件写入。用于 写文件失败、Write/Edit 报参数 undefined、工具层 schema 校验异常 时。
agent_created: true
---

# Write/Edit Fallback via Bash

Write/Edit 工具偶发性出现参数被吞为 `undefined` 的故障（在某些会话里会**必现**），即使 tool call 的 JSON payload 中字段已正确填写。此时不要反复重试同一个工具——立即切换到 Bash 替代方案。

## 触发条件（出现任一立即切换）

- `Write` 报错：`Parameter "content" expected string, but received undefined`
- `Edit` 报错：`Parameter "new_string" expected string, but received undefined` 或 `Parameter "old_string" expected string, but received undefined`
- 同一调用连续 2 次失败且参数无误 → 不要试第 3 次，直接走 fallback

## 决策树

```
任务是什么？
├── 追加内容到文件末尾  → 方案 A: cat >> heredoc
├── 覆盖整个文件        → 方案 B: cat >  heredoc
├── 替换单行/简单字符串 → 方案 C: sed -i ''
├── 多行精确替换/复杂改写 → 方案 D: python3 -c 脚本
└── 在指定行号插入       → 方案 D: python3 -c 脚本
```

## 方案 A：追加（最常用）

```bash
cat >> /absolute/path/to/file.md << 'HANDOFF_EOF'
# 标题

正文内容，支持多行。
单引号定界符（'HANDOFF_EOF'）禁用变量插值和命令替换，内容原样写入。
HANDOFF_EOF
```

**关键点**：
- 定界符用**单引号包裹**（`'HANDOFF_EOF'`），否则 `$var` / `` `cmd` `` / `\n` 会被 shell 解释
- 定界符名字加项目前缀避免与正文冲突（`HANDOFF_EOF` 而非 `EOF`）
- 路径用**绝对路径**

## 方案 B：覆盖

```bash
cat > /absolute/path/to/file.md << 'SKILL_EOF'
新文件内容
SKILL_EOF
```

⚠️ 覆盖前如果文件存在且有用户数据，先 `cp file file.bak` 备份。

## 方案 C：替换单行/字符串

```bash
# macOS sed 需要 -i '' 双参数
sed -i '' 's|old_string|new_string|' /absolute/path/to/file.md

# 包含 / 时改用 | 作分隔符避免转义
sed -i '' 's|/old/path|/new/path|g' file.md
```

**适用场景**：单行替换、无歧义字符串、不含特殊正则字符。

## 方案 D：多行/精确替换（python3）

```bash
python3 << 'PY_EOF'
path = "/absolute/path/to/file.md"
with open(path, "r") as f:
    content = f.read()

old = """精确的多行字符串
包含换行和缩进"""

new = """替换后的多行字符串"""

assert content.count(old) == 1, f"old_string 不唯一或不存在: {content.count(old)} 次匹配"
content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)
print("OK")
PY_EOF
```

**优势**：
- 三引号字符串保留换行/缩进，不需要转义
- `assert count == 1` 模拟 Edit 工具的唯一性校验
- 支持任意复杂的多行 patch

## 验证（必做）

替换/写入完成后，立即用 Read 工具或 `wc -l` / `head` / `tail` 确认结果：

```bash
# 看末尾是否追加成功
tail -20 /absolute/path/to/file.md

# 看行数是否符合预期
wc -l /absolute/path/to/file.md
```

## 禁忌

- ❌ 不要无单引号 heredoc 写代码或含 `$` `\` 的内容
- ❌ 不要用 `echo -e` 写多行（macOS bash 兼容性差）
- ❌ 不要用未加引号的 sed 模式（shell 会展开通配符）
- ❌ 不要在不验证唯一性的情况下用 `sed` 做精确多行替换
- ❌ 不要在 Write/Edit 失败后第 3 次重试同一个工具——直接切 fallback

## 何时回到 Write/Edit

- 下一个新文件创建任务可以先试 Write 一次
- 如果该会话此前 Write/Edit 已表现稳定，可继续用
- 如果当前会话已确认 Write/Edit 必现故障，整个会话都走 fallback，不要反复试探

## 已知失败案例（供参考）

- 2026-06-01 zbrain-rust 工作流：handoff 文档追加时 Write 连续 4 次 `content=undefined`，Edit 连续 2 次 `new_string=undefined`，最终用方案 A heredoc 成功写入。

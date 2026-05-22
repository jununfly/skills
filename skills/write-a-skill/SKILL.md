---
name: write-a-skill
description: 新建一个 Agent Skill，并确保它有 正确的结构、渐进式暴露方式和绑定的资源。用于 用户想要创建一个新的skill 时。
---

# Writing Skills

## SOP

1. **收集需求** - 询问用户:
   - 这个 `skill` 是做什么的？
   - 有没有具体的使用场景？
   - 用 可执行脚本 实现，还是仅`指令`？
   - 要包含哪些引用资源？

2. **`skill`草稿** - 创建:
   - SKILL.md，里面只放简洁的`指令`
   - 如果内容会超过500行，保存到另外的引用文件中
   - 如果有必要，用`utility scripts`实现确定性操作

3. **让用户审查** - 展示草稿，询问用户:
   - 这个满足你的需求吗？
   - 有没有遗漏或不清晰之处？
   - 有没有要细化或简化的章节？

## Skill Structure

```
skill-name/
├── SKILL.md           # 主要 `指令` (必须有)
├── REFERENCE.md       # 更多具体细节 (如果有必要)
├── EXAMPLES.md        # 使用示例 (如果有必要)
└── scripts/           # `utility scripts` (如果有必要)
    └── helper.js
```

## SKILL.md Template

```md
---
name: skill-name
description: 它能做什么。用于 [触发器].
---

# Skill Name

## Quick start

[最小的工作示例]

## Workflows

[带checklist的 一步一步的 处理复杂任务]

## Advanced features

[引用另外的独立文件: 详见 [REFERENCE.md](REFERENCE.md)]
```

## Description 的要求

当确定要加载哪个`skill`时，`description`是 **agent能看见的唯一事物**。在`system prompt`中，它和其他已安装的`skill`的`description`放在一起。agent会读取这些`description`，并选择接近用户请求的`skill`。

**Goal**: 只给`agent`必要的信息：

1. 这个`skill`提供了什么能力
2. 什么时候/为什么 触发它(指定的 keyword, contexts, file types)

**Format**:

- 最多 1024 个字符
- 以第三人称写
- 第一句: 它会做什么
- 第二句: "用于 [触发器] 时"

**好的示例**:

```
从PDF文件中提取文本和表格，填充表格，合并文档。用于 处理PDF文件或用户提到PDF文件、表格或文档提取 时。
```

**不好的示例**:

```
文档助手。
```

不好的示例，会让 agent 没有办法区分这个`skill`和其他的`skills`。

## When to Add Scripts

Add utility scripts when:

- 操作是确定性的(验证, 格式化)
- 会反复产生相同的代码
- 需要显式处理的各种错误

对比 临时生成的代码，Scripts可以节约tokens并提高可靠性。

## When to Split Files

Split into separate files when:

- SKILL.md 超过了 100 行
- 内容有不同的 `domains` (金融 vs 销售 schemas)
- Advanced features 很少用到

## Review Checklist

草稿完成后, 检查：

- [ ] Description 包含触发器("用于 ... 时")
- [ ] SKILL.md的全部内容在100行之内
- [ ] 没有时效性的信息
- [ ] 前后一致的术语
- [ ] 有具体的举例
- [ ] 引用文件或链接的深度只有1
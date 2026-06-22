---
title: "zj-roadmap-driven"
description: "路线图驱动开发——以地图导航形式，帮助 Agent 正确理解全貌，始终与 Human 保持地图颗粒度对齐"
triggers:
  - 路线图驱动
  - roadmap driven
---

# zj-roadmap-driven — 路线图驱动开发

**目标：** 在复杂任务场景中，用路线图（树形节点 + 决策记录）作为 Agent 和 Human 的共享心智模型。避免持续对话导致的目标偏离——每一步都在地图上留下足迹。

**核心原则：**
1. **JSON 是唯一真相源**，Markdown 是只读渲染视图
2. **每个节点有编号**（1, 1-1, 1-1-1, …），方便 Human 和 Agent 快速定位
3. **每个节点有状态 checkbox**（[ ] / [~] / [x] / [!]），一眼识别进度
4. **节点分模式**：EXPLORE（探索子树）vs EXPLOIT（深入施工）
5. **决策随节点落盘**，形成可追溯的决策历史

## 工作流

```
Human 提方向 → Agent 建 roadmap JSON → Agent 渲染 section 到 md
    ↓
Agent 每做一个决策 → 调用 `decide` 写入节点 → 调用 `render` 更新 md
    ↓
Human 看 md 里的树和决策表 → 确认或纠正 → Agent 继续
    ↓
Agent 完成一个子任务 → 调用 `update` 打勾 → 调用 `render` 更新 md
```

**关键规则：**
- **Agent 每次完成实质工作后，必须 `render` 更新 md 文件。** 这是 Human 看到进度的唯一窗口。
- **Agent 做任何方向性决策前，先 `decide` 记录。** 决策不落盘 = 没发生。
- **Human 随时可以通过 `tree` + `decisions` 了解全貌，无需翻对话历史。**

## 数据结构

### 节点字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 编号，如 `1`, `1-1`, `1-1-1` |
| `label` | string | 节点名称 |
| `status` | string | `pending` / `in_progress` / `completed` / `blocked` |
| `mode` | string | `explore`（探索） / `exploit`（深挖） |
| `parent` | string\|null | 父节点 id，根节点为 null |
| `children` | list | 子节点 id 列表 |
| `decisions` | list | 决策记录 `[{q, answer, note}]` |
| `notes` | string | 自由备注 |

### 状态图标

| 状态 | 图标 | 含义 |
|------|------|------|
| `pending` | `[ ]` | 待处理 |
| `in_progress` | `[~]` | 施工中 |
| `completed` | `[x]` | 已完成 |
| `blocked` | `[!]` | 被阻塞 |

### 模式含义

| 模式 | 含义 |
|------|------|
| `explore` | 子树还在探索中——方向、范围、优先级未定 |
| `exploit` | 子树方向已确定——正在深入施工 |

### JSON Demo

参见 `demos/roadmap_demo.json`——基于「AI-Native 个人可复利工具系统」的实际路线图。

### Markdown Section Demo

参见 `demos/ZJ_ROADMAP_section_demo.md`——由 `roadmap.py` 从 JSON 自动渲染的标准输出。

## 确定性操作

所有操作通过 `roadmap_cli.py` 执行。每个命令输入确定 → 输出确定。

**Python 依赖：** 无第三方依赖，仅需 Python 3.8+ 标准库。

### 初始化

```bash
# 创建新路线图
python roadmap_cli.py init <json_path> --title "项目名称" [--description "描述"] [--md-file "关联的md文件.md"]
```

### 节点 CRUD

```bash
# 添加子节点
python roadmap_cli.py add <json_path> <parent_id> "<label>" [--status pending] [--mode explore]

# 更新节点属性（只更新传入的字段）
python roadmap_cli.py update <json_path> <node_id> --status completed
python roadmap_cli.py update <json_path> <node_id> --label "新标签" --notes "备注内容"

# 删除节点及所有子节点
python roadmap_cli.py delete <json_path> <node_id>

# 查看节点详情 (JSON)
python roadmap_cli.py get <json_path> <node_id>
```

### 决策记录

```bash
# 为节点添加决策
python roadmap_cli.py decide <json_path> <node_id> "问题" "答案" ["备注"]

# 列出所有决策（或指定节点）
python roadmap_cli.py decisions <json_path>
python roadmap_cli.py decisions <json_path> <node_id>
```

### 渲染

```bash
# 输出 Markdown section 到 stdout
python roadmap_cli.py section <json_path>

# 将 section 写入关联的 md 文件（通过 link 设置）
python roadmap_cli.py render <json_path>

# 关联 md 文件
python roadmap_cli.py link <json_path> <md_file>
```

### 导航

```bash
# 树形视图
python roadmap_cli.py tree <json_path>
python roadmap_cli.py tree <json_path> <node_id>    # 从指定节点开始
python roadmap_cli.py tree <json_path> <node_id> --depth 3

# 从根到节点的路径
python roadmap_cli.py path <json_path> <node_id>

# 兄弟节点
python roadmap_cli.py siblings <json_path> <node_id>

# 当前施工点（第一个 in_progress 的叶子节点）
python roadmap_cli.py focus <json_path>
```

### 验证与统计

```bash
# 数据完整性验证
python roadmap_cli.py validate <json_path>

# 统计信息
python roadmap_cli.py stats <json_path>
```

### 从已有 md 导入

```bash
# 从包含 ROADMAP_TREE 标记的 md 文件导入
python roadmap_cli.py import <json_path> <md_file>
```

## Agent 使用示例

```
# 场景：Human 说「把文章处理后端走通」

# 1. 先在路线图上定位
python roadmap_cli.py tree roadmap.json 1-1-1

# 2. 添加新节点
python roadmap_cli.py add roadmap.json 1-1-1 "文章处理后端流水线" --status in_progress

# 3. 记录决策
python roadmap_cli.py decide roadmap.json 1-1-1-5 "后端用什么？" "Python + FastAPI" "轻量够用"

# 4. 施工完成后更新状态
python roadmap_cli.py update roadmap.json 1-1-1-5 --status completed --notes "API: POST /articles/convert"

# 5. 更新 Human 的 md 视图
python roadmap_cli.py render roadmap.json
```

## Script 路径

Skill 脚本位于 skill 目录本身，Agent 运行时按 skill 目录计算路径：

```
<skill_dir>/roadmap.py        # 核心库
<skill_dir>/roadmap_cli.py    # CLI 入口
```

Agent 在 Skill 加载后，用 `$SKILL_DIR` 或绝对路径定位脚本。

## 与 zj-grill-me 配合

`zj-roadmap-driven` 是 `zj-grill-me` 的搭档：
- `zj-grill-me` 负责逐层拷问，到达决策树叶子节点
- `zj-roadmap-driven` 负责把每层决策沉淀到路线图 JSON + md section
- 两者交替：grill 一个 Q → roadmap 记录决策 → grill 下一个 Q

## Notes

- JSON 是唯一真相源。**永远不要手动编辑渲染后的 md 树。**
- md section 由 `render` 命令完全重写，手动修改会被覆盖。
- 删除节点会递归删除所有子节点，操作前确认。
- 如果路线图 JSON 不存在，Agent 应先用 `init` 创建。

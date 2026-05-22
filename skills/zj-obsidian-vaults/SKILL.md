---
name: zj-obsidian-vaults
description: 查找多个Obsidian Vault的保存路径
origin: zj
---

# zj-obsidian-vaults - 多个 Obsidian Vault 管理

管理多个 Obsidian Vault，每个 vault 都是由 zj-obsidian-wiki 维护的独立知识库。

## 预定义 Vault

在 `vaults.yaml` 中预定义以下 vault：

```
Obsidian vaults/
├── 生活/              # 生活
├── 工作/              # 工作
├── 项目/              # 项目
└── 读书笔记/           # 读书笔记
```

## 核心操作流程

### 1. 获取 Vaults 根路径

- 首先检查用户是否指定过 "Obsidian vaults" 的路径
- 如果没有指定，询问用户具体的路径

### 2. 检查知识库群

根据 `vaults.yaml` 的记录：
1. 列出所有已配置的 vault
2. 检查各个 vault 是否存在且符合 zj-obsidian-wiki 要求
3. 不符合要求的 vault 条目需要从`vaults.yaml`中删除前询问用户确认

### 3. Vault 操作

当用户提到特定 vault 时（如 "知识库-生活"）：
1. 通过 `vaults.yaml` 查找对应的 vault
2. 如果不存在，提示用户是否创建
3. 如果存在，使用 zj-obsidian-wiki 操作该 vault

## 重要原则

- 有问题不知道怎么处理时，询问用户不要自动处理
- 删除或修改 vault 条目前必须确认
- 所有 vault 操作都通过 zj-obsidian-wiki 进行

---
name: rust-slice-completion-sop
description: ZBrain Rust 重构项目中"完成一个切片"的标准作业流程——从红测试到三连绿再到 commit/tag/memory 一气呵成。用于 在 zbrain-rust worktree 中按 docs/plans/20260526/ 里的切片计划推进任意一片实现（slice-N），尤其是涉及 BrainEngine 后端、SQL 方言适配、迁移协议、跨 crate workspace 改动时。
agent_created: true
---

# Rust Slice Completion SOP

> 一切片一闭环：红测试 → 实现 → 三连绿 → commit + tag + memory。
> 节奏稳了，切片就不会拖。

## 适用场景

- 项目路径：`/Users/bilibili/Documents/workspace/jununfly/zbrain-rust/`（git worktree，分支 `rust-rewrite`）
- 任意 `docs/plans/20260526/sliceN-*.md` 切片
- 任何 BrainEngine 后端（PostgresEngine / LibsqlEngine / 未来的 Turso、SurrealDB 等）新增方法或新表 CRUD

## 流程（按顺序执行，禁止跳步）

### Step 0 — 上下文加载
1. 读上一切片 memory 末尾的"切片 N 上下文快照"段（若有）
2. 读 `docs/plans/20260526/sliceN-*.md`（本切片计划）
3. `git status` 确认 worktree 干净，分支正确

### Step 1 — 红测试先行（TDD）
1. 在 `crates/<crate>/tests/` 下按方法拆分测试文件（lifecycle 与 CRUD 分文件，单文件 ≤ 300 行）
2. 每个用例用 `tempfile::NamedTempFile` 隔离
3. 跑一次确认全红：`cargo test -p <crate> --test <test_file>`

### Step 2 — 镜像基线对照
1. 找到对位的参考实现（如 LibsqlEngine 对照 PostgresEngine），完整重读
2. 抽取共有契约：trait 签名、错误语义、空值约定、SQL 形状
3. 标注后端差异点（方言、参数风格、RETURNING 支持等）
4. **结构扩字段兼容检查**：若本切片扩了 `Page` / `PageInput` / `PageFilters` 等结构体的字段：
   - 给 input/filter 类型加 `#[derive(Default)]`
   - 所有存量字面量追加 `..Default::default()` 而非列举新字段
   - 逐个跑现有测试（`engine_object_safety` / `*_engine_page_crud`）确认不爆破
   - `row_to_page` 新字段先用 placeholder（`None`/`String::new()`/`Map::default()`），真实 decode 推到 SELECT 切片

### Step 3 — 实现切片
1. 按方法逐个落地，每写一个就跑该方法的测试
2. 命名冲突防御：若模块名与 extern crate 同名，全部用 `::crate::Item` 绝对路径
3. SQL 文本宁可冗长也别为了 DRY 牺牲可读性

### Step 4 — 三连绿（缺一不可）
```bash
cd /Users/bilibili/Documents/workspace/jununfly/zbrain-rust
cargo build --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```
- 第一关失败 → 改代码
- 第二关失败 → 检查测试假设
- 第三关失败 → **多半是 pedantic lint**：
  - `doc_markdown`：给 doc 注释里的标识符加反引号（如 `` `SQLite` `` / `` `InMemoryEngine` ``）
  - `default_trait_access`：`Default::default()` 改为显式 `Map::default()` / `Vec::default()` 等
  - `cast_possible_wrap`：`as i64` 改 `i64::try_from(x)?`
  - 详见 REFERENCE.md 的 clippy 修复清单

### Step 5 — 切片收尾
```bash
git add -A
git status                                          # 复核改动面
git commit -m "slice-N: <one-line summary>

- bullet 1
- bullet 2
- 测试结果：X/X 全绿"
git tag rust-slice-N
git log --oneline -6                                # 验证 tag 链连续
```

### Step 6 — Memory 笔记
追加到当前 workspace 的 `.workbuddy/memory/YYYY-MM-DD.md`：
- 产物清单（文件 + 行数）
- 关键技术决策（为什么这么选）
- 踩坑记录（含修复方式）
- 下一切片的"上下文快照"段（给下次会话用）

### Step 7 — Skill 反思
- 本切片有没有暴露 SOP 漏洞？有 → 立即更新本 skill
- 有没有可复用的"方言适配清单"或"trait 实现模板"？有 → 追加到 REFERENCE.md

## 反模式（禁止）

- ❌ 跳过测试直接写实现（切片 4b 之前的教训）
- ❌ 用 `Edit` 工具写超过 200 行的新文件（容易丢字符，改用 `Bash` heredoc 分段）
- ❌ `cargo build` 过了就 commit（必须三连绿）
- ❌ commit 不打 tag（tag 链断了切片溯源失效）
- ❌ 切片 commit 里夹带"顺手优化"（破坏 commit 的可回滚性）

## 参考

- 详细方言适配清单、clippy 常见 lint、SQL 模板见 `REFERENCE.md`
- 历史切片完整记录见 `docs/plans/20260526/sliceN-*.md`
- 标杆切片实现：`crates/zbrain-core/src/postgres.rs`（PG 基线）、`crates/zbrain-core/src/libsql.rs`（SQLite 镜像）

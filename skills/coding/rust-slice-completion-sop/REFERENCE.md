# Rust Slice Completion SOP — Reference

## 1. PostgreSQL → SQLite 方言适配清单

| PostgreSQL | SQLite | 备注 |
|---|---|---|
| `BIGSERIAL` / `BIGINT GENERATED ALWAYS AS IDENTITY` | `INTEGER PRIMARY KEY AUTOINCREMENT` | SQLite 自增必须用这个组合 |
| `TIMESTAMPTZ DEFAULT now()` | `TEXT DEFAULT CURRENT_TIMESTAMP` | SQLite 无原生时间类型，存 ISO8601 文本 |
| `$1`, `$2` ... 占位符 | `?1`, `?2` ... | libsql 用 `?N` 风格 |
| `LIMIT NULL`（表无限） | `LIMIT -1` | SQLite 不认 `NULL` |
| `ON CONFLICT(cols) DO UPDATE SET col = EXCLUDED.col` | 同语法，`excluded` 小写 | SQLite 3.24+ 支持 UPSERT |
| `RETURNING col` | `RETURNING col` | SQLite 3.35+ 支持，libsql 0.9 已含 |
| `sqlx::migrate!()` 嵌入迁移 | `PRAGMA user_version` + `include_str!` DDL | 手卷更轻，不依赖 sqlx |
| `Row::get::<Type, _>("column")` 按名取列 | `Row::get::<Type>(0)` 按位置取列 | libsql 当前仅支持位置索引 |

## 2. Clippy `doc_markdown` 修复清单

Clippy pedantic lint 要求 doc 注释中出现的 CamelCase / snake_case 标识符加反引号，否则报错。

常见触发词及修复方式：

| 原文 | 修复后 |
|---|---|
| `SQLite` | `` `SQLite` `` |
| `PostgreSQL` | `` `PostgreSQL` `` |
| `init_schema` | `` `init_schema` `` |
| `Page CRUD` | `` `Page CRUD` `` |
| `resolve_slugs` | `` `resolve_slugs` `` |
| `sqlx::migrate` | `` `sqlx::migrate` `` |
| `LibsqlEngine` | `` `LibsqlEngine` `` |
| `BrainEngine` | `` `BrainEngine` `` |

**修复策略**：`cargo clippy` → 数警告 → 批量 `Edit` 加反引号 → 重跑确认收敛。通常 2–3 轮可清零。

## 3. 模块名与 extern crate 同名冲突

当模块名 `mod libsql` 与依赖 `libsql = "0.9"` 同名时，模块内所有引用必须使用绝对路径：

```rust
// ❌ 编译器会解析到本模块
use libsql::Builder;

// ✅ 绝对路径前导冒号
use ::libsql::Builder;
::libsql::params![...]
::libsql::rows::Rows
```

## 4. 手卷 Migration 协议模板

```rust
async fn init_schema(&self) -> Result<()> {
    let conn = self.connection()?;
    let version: i32 = conn
        .query("PRAGMA user_version", ::libsql::params![])
        .await?
        .next()
        .await?
        .map(|r| r.get::<i32>(0))
        .transpose()?
        .unwrap_or(0);

    if version < 1 {
        conn.execute_batch(include_str!("../migrations-sqlite/0001_init.sql"))
            .await?;
        conn.execute("PRAGMA user_version = 1", ::libsql::params![])
            .await?;
    }
    Ok(())
}
```

新增迁移时：新增 `000N_name.sql` 文件 + 在 `init_schema` 中追加 `if version < N` 块。

## 5. 测试隔离模板

```rust
#[tokio::test]
async fn test_name() -> Result<()> {
    let tmp = tempfile::NamedTempFile::new()?;
    let engine = LibsqlEngine::new(tmp.path().to_str().unwrap());
    engine.connect().await?;
    engine.init_schema().await?;
    // ... test logic ...
    engine.disconnect().await?;
    Ok(())
}
```

每个测试用独立临时文件，避免并发写冲突。

## 6. Git Tag 命名规范

| 格式 | 示例 | 含义 |
|---|---|---|
| `rust-slice-N` | `rust-slice-5` | 单一切片 |
| `rust-slice-Na` / `rust-slice-Nb` | `rust-slice-4a`, `rust-slice-4b` | 同一逻辑切片拆分为多步 |

tag 链必须连续：`rust-slice-1` → `rust-slice-2` → ... → `rust-slice-N`

## 7. Commit Message 模板

```
slice-N: <one-line imperative summary>

- Bullet 1: what was added/changed
- Bullet 2: key decision or adaptation
- Bullet 3: dialect/migration details (if applicable)
- Test results: lifecycle X/X + CRUD Y/Y = Z/Z all green
```

尾部不加 emoji，不加"Co-authored-by"。

## 8. Clippy 其他常见 pedantic lint

| Lint | 触发场景 | 修复 |
|---|---|---|
| `default_trait_access` | `Value::Object(Default::default())` | `Value::Object(Map::default())`，并 `use serde_json::Map` |
| `cast_possible_wrap` | `usize as i64`（多迁移 enumerate 索引转 SQL 参数） | `i64::try_from(idx).expect("migration index overflow")` |
| `similar_names` | 函数内同时存在 `page` 与 `pages` 等高相似变量 | 改其中一个为更具语义的名字（如 `pages` → `existing_pages`） |
| `must_use_candidate` | const helper 函数返回值未消费 | 在 fn 前加 `#[must_use]` 或调用处用 `let _ =` |

## 9. 多迁移加载架构模板

当一个后端积累了多条 SQL 迁移（0001 / 0002 / 0003 …）时，避免 N 个 `if version < N` 块的重复，改用数组 + enumerate：

```rust
const MIGRATIONS: &[&str] = &[
    include_str!("../migrations-sqlite/0001_init.sql"),
    include_str!("../migrations-sqlite/0002_pages_full_schema.sql"),
    // 0003_…
];

async fn init_schema(&self) -> Result<()> {
    let conn = self.connection()?;
    let mut version: i64 = conn
        .query("PRAGMA user_version", ::libsql::params![])
        .await?
        .next()
        .await?
        .map(|r| r.get::<i64>(0))
        .transpose()?
        .unwrap_or(0);

    for (idx, sql) in MIGRATIONS.iter().enumerate() {
        let target = i64::try_from(idx + 1)
            .expect("migration index overflow");
        if version < target {
            conn.execute_batch(sql).await?;
            conn.execute(
                &format!("PRAGMA user_version = {target}"),
                ::libsql::params![],
            )
            .await?;
            version = target;
        }
    }
    Ok(())
}
```

**关键点**：
- `try_from` 而非 `as` 转换，规避 `clippy::cast_possible_wrap`
- 每条迁移执行后立即写 `PRAGMA user_version` 形成原子边界（即使下一条失败，已执行的不会重跑）
- SQLite trigger 限制：BEFORE trigger **不能**用 `NEW.col := ...` 赋值（PG 可以），必须改成 AFTER INSERT/UPDATE trigger 内部对刚动过的行做二次 `UPDATE`

## 10. 结构扩字段切片模板

当切片任务是给 `Page` / `PageInput` / `PageFilters` 等结构体扩字段（如 slice 6a S2 把 Page 从 7 字段扩到 24 字段）时：

```rust
// ❶ input 类型加 Default 派生
#[derive(Debug, Clone, Default)]
pub struct PageInput {
    pub page_type: String,
    pub title: String,
    pub compiled_truth: String,
    // 新增字段全部 Option<…>
    pub slug: Option<String>,
    pub frontmatter: Option<serde_json::Value>,
    // ...
}

// ❷ 存量调用方零侵入升级
let input = PageInput {
    page_type: "note".to_string(),
    title: "x".to_string(),
    compiled_truth: "y".to_string(),
    ..Default::default()  // ← 唯一新增的一行
};

// ❸ row_to_page 新字段先 placeholder，真实 decode 推到下一切片
fn row_to_page(row: &Row) -> Result<Page> {
    Ok(Page {
        id: row.get(0)?,
        slug: row.get(1)?,
        // ... 现有 7 列保持原样
        // 新增 17 字段 placeholder
        frontmatter: serde_json::Value::Object(serde_json::Map::default()),
        content_hash: None,
        emotional_weight: None,
        // ...
    })
}
```

**关键点**：
- `Page` 若含 `Option<f64>` 或 `serde_json::Value`，取消 `Eq` 派生（这俩不实现 `Eq`），保留 `PartialEq`
- 测试文件必须显式 `use zbrain_core::BrainEngine`，否则 `.put_page()` 报 E0599
- 日期字段在结构扩展切片用 `String`（ISO-8601），避免临时引入 chrono 拉扯依赖图

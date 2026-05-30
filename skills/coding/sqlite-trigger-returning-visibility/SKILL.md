---
name: sqlite-trigger-returning-visibility
description: |
  SQLite trigger 时机（BEFORE vs AFTER）与外层 UPDATE/INSERT/DELETE `RETURNING` 投影
  的可见性规则。用于 想用 trigger 自动维护衍生列（如 generation / version / updated_at）
  并希望外层语句的 RETURNING 直接返回更新后的值 时，避免落入"AFTER trigger 写入持久化
  但 RETURNING 看不到"的陷阱。
agent_created: true
---

# SQLite Trigger Timing for RETURNING Visibility

## TL;DR（先记结论）

想让 trigger 维护的列在外层语句的 `RETURNING` 中可见，**用 `BEFORE` trigger**，不要用 `AFTER` trigger。
- `AFTER UPDATE` trigger 的 body 在外层 UPDATE 的 RETURNING projection **之后**才执行 → 持久化生效，但 RETURNING 看不到。
- `BEFORE UPDATE` trigger 的 body 在 RETURNING projection **之前**执行 → 持久化生效，且 RETURNING 看到新值。
- BEFORE trigger 内**不能直接给 NEW.col 赋值**（NEW 在 BEFORE UPDATE 中只读），但**可以**用嵌套 `UPDATE t SET col = ... WHERE id = NEW.id` 写同行 —— 这是绕过"NEW 只读"约束的标准技巧。

## 何时用这条经验

- 你正在为某张表写 trigger 维护衍生列：`generation`、`version`、`row_hash`、`updated_at`、`search_index`、审计字段……
- 你的应用层用 `UPDATE ... RETURNING ...` 或 `INSERT ... ON CONFLICT ... RETURNING ...` 一次拿到写入后的状态（典型 UPSERT + 立即读取场景）。
- 你看到 trigger 持久化已生效（再次 SELECT 能读到新值），但同一语句的 RETURNING 拿到的是旧值 → 立刻怀疑 trigger 时机。

## 常见错误论断（务必小心）

> "BEFORE UPDATE trigger 不能修改 NEW，所以维护衍生列只能用 AFTER UPDATE。"

**这条论断是错的**。它混淆了两件事：
1. BEFORE UPDATE trigger 中 `NEW.col = ...` 直接赋值在 SQLite 中**确实不允许**（NEW 在 BEFORE UPDATE 是只读的，只有 BEFORE INSERT 可以改 NEW）。
2. 但 BEFORE UPDATE trigger body 内**嵌套** `UPDATE same_table SET col = ... WHERE id = NEW.id` 是完全合法的，且写入对外层 RETURNING 可见。

写代码注释 / migration 注释时不要照抄"BEFORE 不可行"，应该写"BEFORE 不能直接赋值 NEW，但可用嵌套同行 UPDATE 绕过，且为 RETURNING 可见性所必需"。

## 标准范式（Rust + libsql / 任何 SQLite 驱动）

```sql
-- ✅ 推荐：BEFORE UPDATE + 嵌套同行 UPDATE，RETURNING 可见
CREATE TRIGGER bump_generation_update
BEFORE UPDATE OF col_a, col_b, col_c ON my_table
FOR EACH ROW
WHEN NEW.col_a IS NOT OLD.col_a
  OR NEW.col_b IS NOT OLD.col_b
  OR NEW.col_c IS NOT OLD.col_c
BEGIN
    UPDATE my_table
       SET generation = OLD.generation + 1
     WHERE id = NEW.id;
END;
```

```sql
-- ❌ 反范式：AFTER UPDATE，RETURNING 看不到 bump 结果
CREATE TRIGGER bump_generation_update
AFTER UPDATE OF col_a, col_b, col_c ON my_table
FOR EACH ROW
WHEN ...
BEGIN
    UPDATE my_table SET generation = OLD.generation + 1 WHERE id = NEW.id;
END;
```

应用层调用：

```rust
let row = conn.query(
    "UPDATE my_table SET col_a = ?1 WHERE id = ?2 RETURNING id, col_a, generation",
    params![new_a, id],
).await?.next().await?.unwrap();
// 用 BEFORE trigger：generation 是 bump 后的新值
// 用 AFTER trigger：generation 是 bump 前的旧值（虽然下次 SELECT 能读到新值）
```

## 验证范式（最小复现脚本）

如果项目里已经有 AFTER trigger 想验证是否要改 BEFORE，跑下面的 3 步骤验证而不是查文档：

```bash
sqlite3 /tmp/test.db <<'SQL'
CREATE TABLE foo (id INTEGER PRIMARY KEY, val TEXT, gen INTEGER DEFAULT 0);
INSERT INTO foo (id, val, gen) VALUES (1, 'a', 0);

CREATE TRIGGER t_before BEFORE UPDATE OF val ON foo
FOR EACH ROW WHEN NEW.val IS NOT OLD.val
BEGIN
  UPDATE foo SET gen = OLD.gen + 1 WHERE id = NEW.id;
END;

-- 关键观察：RETURNING 返回的 gen 是不是新值？
UPDATE foo SET val = 'b' WHERE id = 1 RETURNING id, val, gen;
-- 期望：1|b|1
SQL
```

切换 `BEFORE` → `AFTER` 重跑，对比 RETURNING 的 gen 列即可下结论。3 分钟搞定，比查 SQLite 文档快。

## WHEN 子句的细节

- `WHEN NEW.col IS NOT OLD.col`（用 `IS NOT` 而非 `<>`）—— 正确处理 NULL，避免任一侧为 NULL 时 `<>` 返回 NULL 导致 trigger 不触发。
- 所有 watched 列都要在 `CREATE TRIGGER ... BEFORE UPDATE OF col1, col2, ...` 列表里，否则即使 WHEN 通过 trigger 也不会触发（OF 列表是第一道筛子）。
- 连续 UPDATE 相同值（`UPDATE foo SET val = 'b'` where val 已经是 'b'）应该**不**触发 bump —— WHEN 子句负责拦截。

## 跨方言对比（避免迁移踩坑）

- **PostgreSQL**：BEFORE trigger 可以直接修改 `NEW`（`NEW.col := ...`），更直观；RETURNING 可见性遵循同样的"BEFORE 可见 / AFTER 不可见"规则。
- **MySQL**：BEFORE trigger 也可直接改 NEW；MySQL 没有 RETURNING（除 MariaDB 10.5+），可见性问题不常见。
- **SQLite**：BEFORE UPDATE 的 NEW 只读，必须用"嵌套同行 UPDATE"绕过。**这是 SQLite 独有的别扭点，从 PG/MySQL 迁过来最容易踩。**

## 自检清单（出 bug 时按顺序排查）

1. trigger 时机是 BEFORE 还是 AFTER？
2. 如果是 AFTER，外层语句用了 RETURNING 吗？如果是 → 改 BEFORE。
3. WHEN 子句用 `IS NOT` 不是 `<>`？
4. 所有 watched 列都在 `OF ...` 列表里？
5. 嵌套 UPDATE 的 WHERE 是 `id = NEW.id` 不是 `id = OLD.id`？（UPDATE 中 id 通常不变两者等价，但语义上 NEW.id 更对）
6. SQLite `PRAGMA foreign_keys = ON` 没影响？（FK 与 trigger 时机正交，但 CASCADE 触发的 UPDATE 同样受这条规则约束）

## 来源 / 真实案例

- 项目：`zbrain-rust`，slice S6-T6（commit `6daeb02`，tag `slice-6a-s6-t6-put-page-upsert`）。
- 文件：`crates/zbrain-core/migrations-sqlite/0003_salience_and_full_generation_trigger.sql`（修复后的 BEFORE trigger + 长注释）；`crates/zbrain-core/migrations-sqlite/0002_*.sql`（含错误论断的旧注释，应在下次相关切片一并修正）。
- 现象：`put_page` 走 `INSERT ... ON CONFLICT(slug) DO UPDATE ... RETURNING generation` 返回的 generation 始终是旧值，但 SELECT 能读到新值；改 AFTER → BEFORE 后 RETURNING 返回新值。
- 验证：`/tmp/test_trigger.sql`、`/tmp/test_trigger2.sql`、`/tmp/test_trigger3.sql` 三个最小脚本实测，3 次连续 UPDATE（a→b、b→c、c→c）gen 序列：1、2、2，WHEN 子句正确拦截无变更。

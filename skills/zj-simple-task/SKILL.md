---
name: zj-simple-task
description: 用 临时任务队列 优化Agent的运行时能力：task处理逻辑、context整理和task中断后恢复
origin: zj
---

# zj-simple-task - 临时任务队列管理

通过 YAML 文件管理临时任务队列，优化 Agent 的运行时能力，包括 task 处理逻辑、context 整理和 task 中断后恢复。

## 核心概念

### 任务队列文件

- 默认位置：`{workspace}/todolist.yaml`
- 任务数据结构：
  ```yaml
  - id: <time64_timestamp>  # 使用产生记录时的time64时间戳（13位毫秒级）
    task: <任务内容描述>
    status: pending | completed | failed
    created: <创建时间 ISO格式>
    updated: <更新时间 ISO格式>
  ```

### Time64 时间戳

- 格式：毫秒级时间戳（13位数字）
- 用途：作为 task id，确保唯一性和时间顺序
- 获取方式：`date +%s%3N`（Linux/macOS）

## 使用场景

### 1. 多任务积压

当多个 task 积压时：
- ✅ 只处理第一个 task（队列头部）
- ✅ 其他 task 保存到队列文件
- ✅ 告知用户当前队列状态

### 2. 大任务拆分

当单个 task 过大时：
- ✅ 拆成多个独立的小 task
- ✅ 只处理第一个，其他保存到队列
- ✅ 确保每个 task 可独立执行

### 3. 队列查询

用户想知道队列状态时：
- ✅ 读取并展示所有待处理 task
- ✅ 显示队列统计信息（总数、待处理、已完成）

### 4. 队列处理

用户想处理队列中的 task 时：
- ✅ 支持单次处理（一次一个）
- ✅ 支持批量处理（串行逐个）

## 操作流程

### 1. 增加任务（add）

```bash
# 1. 生成 time64 时间戳
id=$(date +%s%3N)

# 2. 读取现有队列
# 3. 追加新任务
# 4. 写回文件
```

**触发场景**：
- 用户明确说"添加任务"
- Agent 判断需要暂存任务

### 2. 删除任务（delete）

```bash
# 1. 读取队列文件
# 2. 找到指定 id 的任务
# 3. 删除该任务
# 4. 写回文件
```

**触发场景**：
- 用户说"删除任务 id"
- 任务处理成功后自动删除

### 3. 修改任务（update）

```bash
# 1. 读取队列文件
# 2. 找到指定 id 的任务
# 3. 修改任务内容或状态
# 4. 写回文件
```

**触发场景**：
- 用户说"修改任务 id"
- 任务处理失败后标记状态

### 4. 查询任务（list）

```bash
# 1. 读取队列文件
# 2. 格式化输出所有任务
# 3. 显示统计信息
```

**触发场景**：
- 用户问"队列里有什么任务"
- 用户问"有没有待处理任务"

### 5. 单次处理（process-one）

**流程**：
1. 读取队列文件
2. 取出第一个 pending 状态的 task
3. **告知用户**：`开始处理 task[id][1/total]: <task内容>`
4. 执行任务处理
5. 处理成功 → 删除该 task
6. 处理失败 → 标记为 failed，询问用户
7. **询问用户**：是否继续处理下一条？

**关键点**：
- ✅ 严格按队列顺序
- ✅ 一次只读一条
- ✅ 处理前告知用户
- ✅ 处理后询问是否继续
- ✅ 成功后立即删除

### 6. 批量处理（process-batch）

**流程**：
```
while 队列不为空:
    读取第一条 pending task
    告知用户：开始处理 task[id][num/total]: <task内容>
    执行任务处理
    
    if 处理成功:
        删除该 task
        继续处理下一条
    else:
        标记为 failed
        询问用户：是否继续？
        if 用户选择继续:
            continue
        else:
            break
```

**关键点**：
- ❌ **不要一次性读取所有 task**（避免 context 暴涨）
- ✅ 单线程串行处理思路
- ✅ 成功一条继续一条
- ✅ 失败时询问用户
- ✅ 成功后立即删除

## 执行示例

### 示例 1：查询队列

```
用户：队列里有什么任务？
Agent：
📋 任务队列状态：
- 总任务：5个
- 待处理：3个
- 已完成：2个

待处理任务：
1. [1745000000123] 知识库-AI-Coding 摄入 doc1.md
2. [1745000001456] 知识库-AI-Coding 摄入 doc2.md  
3. [1745000002789] 知识库-AI-Coding 摄入 doc3.md
```

### 示例 2：单次处理

```
用户：处理一个任务
Agent：
开始处理 task[1745000000123][1/3]: 知识库-AI-Coding 摄入 doc1.md
... 执行任务 ...
✅ 任务完成，已删除

是否继续处理下一条任务？（还有 2 个待处理）
```

### 示例 3：批量处理

```
用户：处理所有任务
Agent：
开始处理 task[1745000000123][1/3]: 知识库-AI-Coding 摄入 doc1.md
... 执行任务 ...
✅ 成功，已删除

开始处理 task[1745000001456][2/2]: 知识库-AI-Coding 摄入 doc2.md
... 执行任务 ...
❌ 失败：文件不存在

是否继续处理？（还有 1 个待处理）
```

## 重要原则

### 1. 严格顺序

- ✅ 按照 task 在队列中的顺序处理
- ✅ 不跳过、不乱序
- ✅ 先进先出（FIFO）

### 2. 避免暴涨

- ❌ **禁止一次性读取所有 task 到内存**
- ✅ 单次处理时只读一条
- ✅ 批量处理时串行逐条读取

### 3. 即时删除

- ✅ 任务处理成功后**立即删除**对应记录
- ✅ 不要等到最后批量删除
- ✅ 确保失败时可恢复

### 4. 用户确认

- ✅ 单次处理后询问是否继续
- ✅ 批量处理失败时询问是否继续
- ✅ 删除/修改任务前确认（除非是自动删除）

### 5. 状态追踪

- ✅ 使用 status 字段标记任务状态
- ✅ pending → completed / failed
- ✅ 更新 updated 时间戳

## 技术实现

### 读取队列

```python
import yaml
from pathlib import Path

def read_queue(file_path):
    """读取队列文件"""
    path = Path(file_path)
    if not path.exists():
        return {'tasks': [], 'summary': {}}
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
```

### 写入队列

```python
import yaml
from pathlib import Path

def write_queue(file_path, data):
    """写入队列文件"""
    # 遵循 qclaw-text-file skill 规范
    # 使用脚本写入，不直接用 write 工具
    pass
```

### 生成 Task ID

```bash
# Linux/macOS
id=$(date +%s%3N)

# 示例输出：1745000000123（13位毫秒时间戳）
```

### 添加任务

```python
import time

def add_task(queue_data, task_content):
    """添加新任务"""
    task_id = int(time.time() * 1000)  # time64
    new_task = {
        'id': task_id,
        'task': task_content,
        'status': 'pending',
        'created': datetime.now().isoformat(),
        'updated': datetime.now().isoformat()
    }
    queue_data['tasks'].append(new_task)
    update_summary(queue_data)
    return task_id
```

### 删除任务

```python
def delete_task(queue_data, task_id):
    """删除任务"""
    queue_data['tasks'] = [
        t for t in queue_data['tasks'] 
        if t['id'] != task_id
    ]
    update_summary(queue_data)
```

### 更新任务状态

```python
def update_task_status(queue_data, task_id, status):
    """更新任务状态"""
    for task in queue_data['tasks']:
        if task['id'] == task_id:
            task['status'] = status
            task['updated'] = datetime.now().isoformat()
            break
    update_summary(queue_data)
```

### 更新统计信息

```python
def update_summary(queue_data):
    """更新统计信息"""
    tasks = queue_data.get('tasks', [])
    queue_data['summary'] = {
        'total': len(tasks),
        'pending': sum(1 for t in tasks if t['status'] == 'pending'),
        'completed': sum(1 for t in tasks if t['status'] == 'completed'),
        'failed': sum(1 for t in tasks if t['status'] == 'failed'),
        'last_updated': datetime.now().isoformat()
    }
```

## 文件写入规范

**必须遵循 qclaw-text-file skill**：

1. **禁止**直接用 `write` 工具写入 `todolist.yaml`
2. **必须**通过脚本写入：
   ```bash
   python3 "{SKILL_DIR}/scripts/write_file.py" \
     --path "{workspace}/todolist.yaml" \
     --content-file "/tmp/_tw_todolist.yaml"
   ```

## 错误处理

### 任务处理失败

1. 标记任务状态为 `failed`
2. 记录错误信息（可添加 `error` 字段）
3. 询问用户是否继续
4. 不删除任务，保留现场

### 队列文件损坏

1. 备份损坏文件
2. 重新初始化空队列
3. 通知用户数据丢失

### 并发冲突

1. 使用文件锁（如 `fcntl.flock`）
2. 读-修改-写操作加锁
3. 避免数据覆盖

## 总结

**zj-simple-task** 的核心价值：

1. **任务暂存**：多任务积压时只处理第一个，其他保存
2. **任务拆分**：大任务拆成小任务，逐个处理
3. **中断恢复**：通过队列文件恢复上下文
4. **Context 保护**：单次只读一条，避免暴涨
5. **即时删除**：成功后立即删除，确保可恢复

遵循以上规范，可以有效优化 Agent 的运行时能力，确保任务处理的可靠性、可恢复性和可维护性。

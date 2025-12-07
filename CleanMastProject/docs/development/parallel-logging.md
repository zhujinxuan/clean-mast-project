# 并行日志系统

CleanMast 实现了线程安全的双输出日志系统，支持多线程并行计算场景。

## 概述

日志系统提供两种输出：
- **终端输出**：彩色格式，便于实时监控
- **JSONL 文件**：结构化日志，便于后续分析和调试

每个工作线程拥有独立的日志文件，避免并发写入冲突。

## 技术架构与设计原理

### 双输出日志架构

CleanMast 使用组合日志系统，通过 `TeeLogger` 将日志同时发送到两个目标：

```julia
create_cleanmast_logger() 返回:
    TeeLogger(
        TerminalLogger,    # 终端彩色输出（基于 TerminalLoggers.jl）
        JSONLFileLogger    # 结构化 JSONL 文件（自定义实现）
    )
```

### 与 Julia 默认日志器的区别

| 特性 | Julia ConsoleLogger | CleanMast 日志系统 |
|------|---------------------|-------------------|
| **输出方式** | 单一终端输出 | 双输出（终端 + 文件） |
| **结构化日志** | 无 | JSONL 格式 |
| **并行支持** | 基础线程安全 | 每线程独立文件 + 锁 |
| **上下文信息** | 文件:行号 | 任务名 + 工作线程 ID |
| **数据分析** | 需手动解析 | 可用 `jq` 查询 |

### 文本显示 vs JSON 序列化

CleanMast 的 `JSONLFileLogger` 与 Julia 默认的 `ConsoleLogger` 在处理 kwargs 时有本质区别：

**ConsoleLogger（文本显示）**：
```julia
# 使用 show(io, value) 转换为文本
for (key, val) in pairs(kwargs)
    show(io, val)  # Julia 为所有类型定义了 show() 方法
end

# 示例输出：
#   buffer = Ptr{UInt8} @0x00007f1f72eb7850
#   encoder_state = DataType
```

Julia 为**所有类型**都定义了 `show()` 方法，因此文本显示永远不会失败。

**JSONLFileLogger（JSON 序列化）**：
```julia
# 使用 JSON.print(io, value) 序列化为 JSON
for (key, value) in kwargs
    entry[key_str] = value  # 调用 JSON 序列化
end
```

JSON 格式**仅支持 6 种数据类型**：
- ✓ `string` → `"text"`
- ✓ `number` → `42`, `3.14`
- ✓ `boolean` → `true`, `false`
- ✓ `null` → `null`
- ✓ `array` → `[1, 2, 3]`
- ✓ `object` → `{"key": "value"}`

JSON 格式**不支持**：
- ❌ `Ptr{Nothing}` - 内存指针
- ❌ `DataType` - 类型对象
- ❌ `Module` - 模块引用
- ❌ `Function` - 函数引用

### 为什么需要类型过滤

当我们在绘图代码中调用 `save("plot.png", figure)` 时，内部库（如 CairoMakie、PNGFiles）会使用 Julia 的日志系统记录调试信息：

```julia
# 用户代码
save(plot_file, fig)

# CairoMakie/PNGFiles 内部可能执行
@debug "Writing PNG" file=path buffer=Ptr{UInt8}(...) encoder_state=SomeType(...)
```

由于我们的 `worker_logger` 是活动日志器，它接收**该线程所有代码的日志消息**，包括第三方库。这些库不知道我们的日志器需要 JSON 兼容数据，因此可能传递：
- 图像缓冲区的内存指针
- 内部编码器状态的类型对象
- 模块或函数引用

尝试序列化这些类型会导致错误：
```
ERROR: Cannot serialize type Ptr{Nothing}
```

### 解决方案：安全的类型处理

`JSONLLogger.jl` 实现了五层防护：

```julia
for (key, value) in kwargs
    # 第 1 层：过滤已知的不可序列化类型
    if value isa Ptr || value isa DataType || value isa Module || value isa Function
        continue
    end

    try
        # 第 2 层：尝试 JSON 序列化
        entry[key_str] = value
    catch e
        try
            # 第 3 层：降级为 string() 转换
            entry[key_str] = string(value)
        catch
            try
                # 第 4 层：使用 show() 转换（Julia 保证所有类型都支持）
                io = IOBuffer()
                show(io, value)
                entry[key_str] = String(take!(io))
            catch
                # 第 5 层：完全跳过
                continue
            end
        end
    end
end
```

这确保：
- ✓ 用户 kwargs（如 `mast="TGL1"`）正确序列化到 JSON
- ✓ 内部库 kwargs（如 `buffer=Ptr{...}`）被安全跳过
- ✓ 未知类型首先尝试 `string()` 转换
- ✓ 如果 `string()` 失败，使用 `show()` 降级（Julia 保证支持所有类型）
- ✓ 日志系统不会因第三方库的内部状态而崩溃

### 设计权衡

| 方案 | 优点 | 缺点 |
|------|------|------|
| **仅文本日志** | 简单，无序列化问题 | 难以自动化分析 |
| **严格 JSON** | 完全结构化 | 内部库 kwargs 会导致崩溃 |
| **类型过滤 + 降级** | 结构化 + 鲁棒性 | 部分 kwargs 可能丢失 |

CleanMast 选择第三种方案，因为：
1. 用户提供的结构化数据（如 `mast=`、`sensor_pairs=`）对分析至关重要
2. 内部库的调试信息（如内存指针）对日志分析无价值
3. 系统鲁棒性优先于记录所有可能的数据

## 基本用法

### 主线程日志

```julia
using ...CleanMastLogging: create_cleanmast_logger
using Logging

# 创建主线程日志器
logger = create_cleanmast_logger(
    job_name="report-reconstruct-meso",
    worker_id=1,
    config_dir=config_dir,
    config_basename=config_basename
)
global_logger(logger)

@info "Starting analysis"
@warn "Low data quality detected"
@error "Failed to load file" exception=(e, catch_backtrace())
```

### 并行任务日志

**重要：** 必须在并行循环前预先创建所有工作线程的日志器，避免竞态条件和资源冲突。

```julia
using ...CleanMastLogging.CleanMastLogger.LogRotation: archive_all_worker_logs

# 1. 在并行工作前归档旧日志（单线程，安全）
@info "Archiving old worker logs before parallel execution"
archive_all_worker_logs(config_dir, config_basename, Threads.nthreads())

# 2. 为所有工作线程预先创建日志器（单线程，安全）
@info "Pre-creating loggers for all worker threads"
worker_loggers = Dict{Int, Any}()
for worker_id in 1:Threads.nthreads()
    worker_loggers[worker_id] = create_cleanmast_logger(
        job_name="analyze-pair",
        worker_id=worker_id,
        config_dir=config_dir,
        config_basename=config_basename
    )
end

# 3. 并行执行任务，复用已创建的日志器
Threads.@threads for idx in 1:total_tasks
    worker_id = Threads.threadid()
    worker_logger = worker_loggers[worker_id]  # 复用现有日志器

    with_logger(worker_logger) do
        @info "Processing task" index=idx total=total_tasks
        # 执行任务...
        @info "Task completed"
    end
end
```

**为什么必须预先创建日志器？**
- 避免多个任务在同一线程创建多个日志器，导致文件句柄冲突
- 避免日志归档的竞态条件（多个线程同时尝试归档同一文件）
- 避免 GC finalizer 中的日志操作导致任务切换错误
- 确保每个线程有且仅有一个日志器实例

## 日志文件结构

### 文件命名规则

日志文件存储在 `{config_dir}/logs/` 目录下：

```
logs/
├── report-reconstruct-meso.1.jsonl   # 主线程和工作线程 1
├── report-reconstruct-meso.2.jsonl   # 工作线程 2
├── report-reconstruct-meso.3.jsonl   # 工作线程 3
└── archive/                          # 归档目录
    ├── report-reconstruct-meso.1.20251012T023045.123.jsonl
    ├── report-reconstruct-meso.2.20251012T023045.456.jsonl
    └── report-reconstruct-meso.3.20251012T023045.789.jsonl
```

- `config_basename`：配置文件基础名（如 `report-reconstruct-meso`）
- `worker_id`：工作线程 ID（`Threads.threadid()`）
- 归档文件带毫秒级时间戳（格式：`yyyymmddTHHMMSS.sss`），避免冲突
- 归档日志默认保留 30 天

### JSONL 格式

每行一个 JSON 对象：

```json
{"job_name":"analyze-pair","worker_id":2,"message":"Analyzing pair","timestamp":"2025-10-12T02:26:22.297Z","level":"Info","index":5,"total":21,"mast":"TGL1","meso":"ERA5"}
{"job_name":"analyze-pair","worker_id":2,"message":"Pair analysis completed","timestamp":"2025-10-12T02:27:00.663Z","level":"Info","mast":"TGL1","meso":"ERA5","sensor_pairs":9}
```

字段说明：
- `job_name`：任务名称，区分不同阶段
- `worker_id`：工作线程 ID
- `message`：日志消息
- `timestamp`：ISO 8601 时间戳
- `level`：日志级别（Info/Warn/Error/Debug）
- 其他字段：通过 `@info "message" key=value` 添加的键值对

### 终端格式

```
[analyze-pair:2] INFO Analyzing pair index=5 total=21 mast=TGL1 meso=ERA5
[analyze-pair:2] INFO Pair analysis completed mast=TGL1 meso=ERA5 sensor_pairs=9
```

格式：`[job_name:worker_id] LEVEL message key=value ...`

颜色：
- `job_name:worker_id`：青色
- `INFO`：绿色
- `WARN`：黄色
- `ERROR`：红色
- `DEBUG`：灰色

## 实际案例：report-reconstruct-meso

### 命令结构

```julia
function execute(config_path::String)
    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    # 1. 主线程日志
    logger = create_cleanmast_logger(
        job_name="report-reconstruct-meso",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename
    )
    global_logger(logger)

    @info "Starting analysis"

    # 2. 归档所有工作线程的旧日志（并行工作前）
    @info "Archiving old worker logs before parallel execution"
    archive_all_worker_logs(config_dir, config_basename, Threads.nthreads())

    # 3. 并行分析阶段
    results = analyze_all_pairs_parallel(config, mast_data, meso_data, config_dir, config_basename)

    # 4. 并行绘图阶段
    create_meso_mast_plots(results, output_dir, mast_data, meso_data, config_dir, config_basename)

    @info "Analysis completed"
end
```

### 分析阶段日志

```julia
function analyze_all_pairs_parallel(config, mast_data, meso_data, config_dir, config_basename)
    total_pairs = length(pairs)
    @info "Created analysis task queue" total_pairs=total_pairs

    # 预先创建所有工作线程的日志器
    @info "Pre-creating loggers for all worker threads"
    worker_loggers = Dict{Int, Any}()
    for worker_id in 1:Threads.nthreads()
        worker_loggers[worker_id] = create_cleanmast_logger(
            job_name="analyze-pair",  # 任务名称
            worker_id=worker_id,
            config_dir=config_dir,
            config_basename=config_basename
        )
    end

    # 并行执行任务，复用已创建的日志器
    Threads.@threads for idx in 1:total_pairs
        worker_id = Threads.threadid()
        worker_logger = worker_loggers[worker_id]  # 复用现有日志器

        with_logger(worker_logger) do
            @info "Analyzing pair" index=idx total=total_pairs mast=mast_name meso=meso_name
            result = analyze_meso_mast_pair(...)
            @info "Pair analysis completed" mast=mast_name meso=meso_name sensor_pairs=length(result.sensor_metrics)
        end
    end
end
```

### 绘图阶段日志

```julia
function create_meso_mast_plots(analysis_results, output_dir, mast_data, meso_data, config_dir, config_basename)
    total_plots = length(analysis_results)
    @info "Creating plot queue" total_plots=total_plots

    # 预先创建所有工作线程的日志器（可复用之前创建的，或创建新的）
    @info "Pre-creating loggers for all worker threads"
    worker_loggers = Dict{Int, Any}()
    for worker_id in 1:Threads.nthreads()
        worker_loggers[worker_id] = create_cleanmast_logger(
            job_name="create-plot",  # 不同任务名称
            worker_id=worker_id,
            config_dir=config_dir,
            config_basename=config_basename  # 相同配置名
        )
    end

    # 并行执行绘图任务，复用已创建的日志器
    Threads.@threads for idx in 1:total_plots
        worker_id = Threads.threadid()
        worker_logger = worker_loggers[worker_id]  # 复用现有日志器

        with_logger(worker_logger) do
            @info "Creating plot" index=idx total=total_plots mast=mast_name meso=meso_name
            create_sensor_scatter_plot(...)
            @info "Plot completed" mast=mast_name meso=meso_name file=basename(plot_file)
        end
    end
end
```

### 日志文件内容示例

`logs/report-reconstruct-meso.2.jsonl`：

```json
{"job_name":"analyze-pair","worker_id":2,"message":"Analyzing pair","timestamp":"2025-10-12T02:26:22.297Z","level":"Info","index":5,"total":21,"mast":"TGL1","meso":"ERA5"}
{"job_name":"analyze-pair","worker_id":2,"message":"Pair analysis completed","timestamp":"2025-10-12T02:27:00.663Z","level":"Info","mast":"TGL1","meso":"ERA5","sensor_pairs":9}
{"job_name":"create-plot","worker_id":2,"message":"Creating plot","timestamp":"2025-10-12T02:27:05.123Z","level":"Info","index":5,"total":21,"mast":"TGL1","meso":"ERA5"}
{"job_name":"create-plot","worker_id":2,"message":"Plot completed","timestamp":"2025-10-12T02:27:38.456Z","level":"Info","mast":"TGL1","meso":"ERA5","file":"TGL1_ERA5_sensors.png"}
```

## 最佳实践

### job_name 命名规范

- **主任务**：使用命令全名（如 `report-reconstruct-meso`）
- **子任务**：使用动词-名词格式（如 `analyze-pair`、`create-plot`）
- **保持简洁**：便于终端显示和日志过滤

示例：
```julia
# 主任务
job_name="report-reconstruct-meso"

# 子任务
job_name="analyze-pair"      # 分析 meso-mast 对
job_name="create-plot"       # 生成图表
job_name="export-data"       # 导出数据
```

### 结构化日志

使用键值对记录重要信息：

```julia
# 好：结构化数据
@info "Analyzing pair" index=idx total=total mast=mast_name meso=meso_name

# 不好：纯文本
@info "Analyzing pair $idx/$total: $mast_name ← $meso_name"
```

结构化日志便于后续解析和分析：

```bash
# 提取所有 TGL1 相关的分析
jq 'select(.mast == "TGL1" and .job_name == "analyze-pair")' logs/*.jsonl

# 统计每个工作线程的任务数
jq -s 'group_by(.worker_id) | map({worker_id: .[0].worker_id, count: length})' logs/*.jsonl
```

### 异常处理

显式记录异常信息：

```julia
try
    result = risky_operation()
catch e
    @error "Operation failed" exception=(e, catch_backtrace())
    rethrow(e)
end
```

JSONL 输出包含完整堆栈跟踪：

```json
{
  "job_name": "analyze-pair",
  "worker_id": 2,
  "message": "Operation failed",
  "level": "Error",
  "exception_type": "MethodError",
  "exception_message": "no method matching foo(::Int64)",
  "stack": [
    "foo @ analysis.jl:123",
    "bar @ analysis.jl:456"
  ]
}
```

### 日志级别选择

- `@info`：正常流程、关键进度（默认显示）
- `@warn`：异常情况但可继续执行
- `@error`：错误需要处理
- `@debug`：详细调试信息（默认不显示终端，仅记录文件）

```julia
@info "Starting analysis" pairs=21              # 关键进度
@debug "Loading configuration" path=config_path # 详细信息
@warn "Low correlation detected" r=0.45         # 数据质量警告
@error "File not found" path=file_path          # 错误
```

## 日志分析

### 查询特定工作线程

```bash
# 查看工作线程 2 的所有日志
cat logs/report-reconstruct-meso.2.jsonl

# 查看工作线程 2 的分析阶段日志
grep '"job_name":"analyze-pair"' logs/report-reconstruct-meso.2.jsonl
```

### 统计任务执行时间

```bash
# 提取分析阶段的开始和结束时间
jq -r 'select(.job_name == "analyze-pair" and (.message | contains("Analyzing") or contains("completed"))) | [.timestamp, .message, .mast, .meso] | @tsv' logs/*.jsonl
```

### 查找错误和警告

```bash
# 查找所有错误
jq 'select(.level == "Error")' logs/*.jsonl

# 查找所有警告
jq 'select(.level == "Warn")' logs/*.jsonl
```

## 配置参数

`create_cleanmast_logger` 完整参数：

```julia
create_cleanmast_logger(;
    job_name::String,              # 必需：任务名称
    worker_id::Int,                # 必需：工作线程 ID
    config_dir::String,            # 必需：配置目录（日志存储路径）
    config_basename::String,       # 必需：配置文件基础名（日志文件前缀）
    terminal_level=Logging.Info,   # 可选：终端日志级别
    file_level=Logging.Debug,      # 可选：文件日志级别
    enable_terminal=true,          # 可选：启用终端输出
    enable_file=true,              # 可选：启用文件输出
    archive_logs=false,            # 可选：启动时归档旧日志（默认 false，使用 archive_all_worker_logs）
    keep_days=30                   # 可选：归档日志保留天数
)
```

**注意：** `archive_logs` 默认为 `false`。应该使用 `archive_all_worker_logs()` 在并行工作前统一归档所有工作线程的日志，而不是在创建日志器时归档。

默认配置适用于大多数场景，通常只需提供前 4 个必需参数。

## 日志归档

使用 `archive_all_worker_logs` 函数在并行工作前统一归档所有工作线程的日志：

```julia
using ...CleanMastLogging.CleanMastLogger.LogRotation: archive_all_worker_logs

# 在并行工作前归档所有工作线程的日志
archive_all_worker_logs(
    config_dir,           # 配置目录
    config_basename,      # 配置文件基础名
    Threads.nthreads();   # 线程数
    keep_days=30          # 可选：保留天数（默认 30）
)
```

**为什么要统一归档？**
- 避免多个线程同时尝试归档同一文件的竞态条件
- 确保归档操作在单线程环境下执行，安全可靠
- 一次性处理所有工作线程的日志文件，更高效

## 参考实现

- `src/Logging/CleanMastLogger.jl`：日志器工厂函数
- `src/Logging/LogRotation.jl`：日志归档和清理功能
- `src/ReportReconstructMeso/CommandReportReconstructMeso.jl`：主命令和并行分析
- `src/ReportReconstructMeso/DataVisualization.jl`：并行绘图
- `src/ReportTimeSeries/TimeSeriesAnalysis.jl`：时序分析并行执行

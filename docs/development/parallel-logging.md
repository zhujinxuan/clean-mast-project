# 并行日志系统

CleanMast 实现了线程安全的双输出日志系统，支持多线程并行计算场景。

## 概述

日志系统提供两种输出：
- **终端输出**：彩色格式，便于实时监控
- **JSONL 文件**：结构化日志，便于后续分析和调试

每个工作线程拥有独立的日志文件，避免并发写入冲突。

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

```julia
Threads.@threads for idx in 1:total_tasks
    worker_id = Threads.threadid()

    worker_logger = create_cleanmast_logger(
        job_name="analyze-pair",
        worker_id=worker_id,
        config_dir=config_dir,
        config_basename=config_basename
    )

    with_logger(worker_logger) do
        @info "Processing task" index=idx total=total_tasks
        # 执行任务...
        @info "Task completed"
    end
end
```

## 日志文件结构

### 文件命名规则

日志文件存储在 `{config_dir}/logs/` 目录下：

```
logs/
├── report-reconstruct-meso.1.jsonl   # 主线程和工作线程 1
├── report-reconstruct-meso.2.jsonl   # 工作线程 2
├── report-reconstruct-meso.3.jsonl   # 工作线程 3
└── archive/                          # 归档目录
    └── report-reconstruct-meso.1.20251012T023045.jsonl
```

- `config_basename`：配置文件基础名（如 `report-reconstruct-meso`）
- `worker_id`：工作线程 ID（`Threads.threadid()`）
- 归档文件带时间戳，默认保留 30 天

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
    # 1. 主线程日志
    logger = create_cleanmast_logger(
        job_name="report-reconstruct-meso",
        worker_id=1,
        config_dir=config_dir,
        config_basename="report-reconstruct-meso"
    )
    global_logger(logger)

    @info "Starting analysis"

    # 2. 并行分析阶段
    results = analyze_all_pairs_parallel(config, mast_data, meso_data, config_dir, config_basename)

    # 3. 并行绘图阶段
    create_meso_mast_plots(results, output_dir, mast_data, meso_data, config_dir, config_basename)

    @info "Analysis completed"
end
```

### 分析阶段日志

```julia
function analyze_all_pairs_parallel(config, mast_data, meso_data, config_dir, config_basename)
    Threads.@threads for idx in 1:total_pairs
        worker_id = Threads.threadid()

        worker_logger = create_cleanmast_logger(
            job_name="analyze-pair",  # 任务名称
            worker_id=worker_id,
            config_dir=config_dir,
            config_basename=config_basename
        )

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
    Threads.@threads for idx in 1:total_plots
        worker_id = Threads.threadid()

        worker_logger = create_cleanmast_logger(
            job_name="create-plot",  # 不同任务名称
            worker_id=worker_id,
            config_dir=config_dir,
            config_basename=config_basename  # 相同配置名
        )

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
    archive_logs=true,             # 可选：启动时归档旧日志
    keep_days=30                   # 可选：归档日志保留天数
)
```

默认配置适用于大多数场景，通常只需提供前 4 个必需参数。

## 参考实现

- `src/Logging/CleanMastLogger.jl`：日志器工厂函数
- `src/ReportReconstructMeso/CommandReportReconstructMeso.jl`：主命令和并行分析
- `src/ReportReconstructMeso/DataVisualization.jl`：并行绘图

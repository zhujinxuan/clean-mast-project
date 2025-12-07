# CleanMast 总体架构

## 概述

CleanMast 采用模块化、可扩展的架构设计，基于函数式编程原则构建。系统围绕数据处理流水线组织，每个处理步骤都是独立的模块，通过标准化的接口进行交互。

## 设计理念

### 1. 模块化设计
- 每个功能模块独立开发和测试
- 清晰的模块边界和职责分离
- 可插拔的组件架构
- 易于扩展和维护

### 2. 函数式编程
- 优先使用纯函数
- 不可变数据结构
- 函数组合和管道操作
- 避免副作用和全局状态

### 3. 配置驱动
- 外部配置文件控制行为
- 可重现的处理流程
- 易于参数调优
- 批处理友好

### 4. 类型安全
- 强类型系统
- 编译时错误检查
- 运行时类型验证
- 清晰的数据契约

## 高层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户接口层                                │
├─────────────────────────────────────────────────────────────┤
│  CLI Interface (CleanMastCli.jl)                          │
│  - Comonicon.jl 基础                                      │
│  - 命令路由和参数解析                                        │
│  - 错误处理和用户反馈                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    命令执行层                                │
├─────────────────────────────────────────────────────────────┤
│  Command Modules                                           │
│  ├─ Project Commands (init, parse-sensors)                │
│  ├─ Process Commands (clean, reconstruct, train)          │
│  ├─ Analyze Commands (timeseries, en, reconstruct)        │
│  └─ Recommend Commands (config generation)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    核心处理层                                │
├─────────────────────────────────────────────────────────────┤
│  Processing Modules                                        │
│  ├─ ParseSensors: 数据解析和标准化                          │
│  ├─ DataClean: 数据清理和质量控制                           │
│  ├─ ReconstructSingleMast: 单测风塔重构                     │
│  ├─ TrainMeso: 中尺度模型训练                               │
│  ├─ ReconstructMeso: 中尺度数据重构                         │
│  ├─ AnalyzeTimeSeries: 时间序列分析                        │
│  └─ ReportGeneration: 报告生成                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    类型和工具层                              │
├─────────────────────────────────────────────────────────────┤
│  Types System                                             │
│  ├─ Configuration Types: 配置文件类型定义                   │
│  ├─ Data Models: 数据模型和结构                            │
│  ├─ Analysis Results: 分析结果类型                         │
│  └─ Utilities: 通用工具函数                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据访问层                                │
├─────────────────────────────────────────────────────────────┤
│  Data I/O                                                 │
│  ├─ File Readers: CSV, TOML, YAML, JLD2                   │
│  ├─ Data Writers: 各种格式的数据输出                        │
│  ├─ Configuration Loaders: 配置文件加载                     │
│  └─ Serialization: 对象序列化和反序列化                     │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件详述

### 1. CLI 接口层 (CleanMastCli.jl)

**职责**：
- 命令行参数解析
- 用户输入验证
- 错误信息格式化
- 帮助信息生成

**设计特点**：
- 基于 Comonicon.jl 的声明式命令定义
- 层次化命令结构 (project, process, analyze, recommend)
- 类型安全的参数传递
- 统一的错误处理机制

**架构模式**：
```julia
# 命令组织模式
Comonicon.@cast module Project
    # project 子命令
    function init(dir::String)
    function parse_sensors(config_path::String)
end

Comonicon.@cast module Process
    # process 子命令
    function clean(project_dir::String)
    function reconstruct_single(config_path::String)
end
```

### 2. 命令执行层

**命令类型**：
- **Project Commands**: 项目管理和初始化
- **Process Commands**: 数据处理和转换
- **Analyze Commands**: 数据分析和报告
- **Recommend Commands**: 配置生成和优化

**执行模式**：
```julia
# 标准命令执行模式
function execute(config_path::String)
    # 1. 加载和验证配置
    config = load_and_validate_config(config_path)

    # 2. 执行核心处理
    result = process_data(config)

    # 3. 保存结果
    save_results(result, config.output)

    # 4. 生成统计报告
    generate_statistics(result)
end
```

### 3. 核心处理层

**模块组织原则**：
- 每个模块专注单一功能
- 模块间通过类型化接口通信
- 支持并行和批处理
- 可配置的算法参数

**模块结构模式**：
```julia
module FeatureName
    include("./FeatureName/Core.jl")                    # 核心算法
    include("./FeatureName/CommandFeatureName.jl")     # 命令接口
    include("./FeatureName/RecommendCommand.jl")       # 配置生成

    export CommandFeatureName, RecommendCommand, Core
end
```

### 4. 类型系统层

**类型组织**：
- **配置类型**: 所有配置文件的类型定义
- **数据模型**: 时间序列、传感器、分析结果
- **接口类型**: 模块间通信的契约
- **工具类型**: 通用的辅助类型

**类型设计原则**：
```julia
# 配置类型模式
struct FeatureConfiguration
    input::InputConfig
    output::OutputConfig
    parameters::ParametersConfig
end

# 序列化接口
function from_dict(::Type{FeatureConfiguration}, dict::Dict)
function to_dict(config::FeatureConfiguration)::Dict
```

## 数据流架构

### 1. 数据流向
```
原始数据文件
    ↓ [ParseSensors]
标准化CSV + 传感器元数据
    ↓ [DataClean]
清理后的数据
    ↓ [TowerShading]
塔影校正数据
    ↓ [ReconstructSingle]
单测风塔重构数据
    ↓ [TrainMeso]
中尺度训练模型
    ↓ [ReconstructMeso]
中尺度重构数据
    ↓ [RepresentativeYear]
代表年校准数据
    ↓ [AnalyzeTimeSeries]
分析报告和结果
```

### 2. 数据格式标准化

**核心数据结构**：
```julia
# 时间序列数据
struct TimeSeriesData
    timestamps::Vector{DateTime}
    data::DataFrame
    sensors::Vector{SensorInfo}
    metadata::Dict{String, Any}
end

# 传感器信息
struct SensorInfo
    name::String
    sensor_type::String
    height::Float64
    direction::String
    unit::String
    statistical_type::String
end
```

**文件格式约定**：
- **数据文件**: CSV 格式，标准化列名
- **传感器配置**: TOML 格式，结构化元数据
- **处理配置**: TOML/YAML 格式，类型安全
- **结果输出**: CSV/JSON/HDF5，多格式支持

### 3. 配置管理

**配置层次**：
```
项目配置 (project level)
    ├─ parse-sensors.toml    # 数据解析配置
    ├─ process-clean.toml    # 数据清理配置
    ├─ train-meso.toml       # 模型训练配置
    └─ analyze-*.yaml        # 分析配置

格式配置 (format level)
    ├─ formats/sensor/       # 传感器格式定义
    ├─ formats/clean/        # 清理规则定义
    └─ formats/analysis/     # 分析模板定义

系统配置 (system level)
    ├─ 默认参数设置
    ├─ 算法参数库
    └─ 质量控制阈值
```

## 错误处理和日志

### 1. 错误处理策略

**错误分类**：
- **配置错误**: 文件不存在、格式错误、参数无效
- **数据错误**: 数据格式不匹配、质量问题
- **算法错误**: 计算失败、收敛问题
- **系统错误**: 内存不足、磁盘空间、权限问题

**错误处理模式**：
```julia
# 统一错误处理
function safe_execute(operation::Function, error_context::String)
    try
        return operation()
    catch e
        log_error(e, error_context)
        return handle_error(e, error_context)
    end
end
```

### 2. 日志系统

**日志级别**：
- **DEBUG**: 详细的诊断信息
- **INFO**: 一般信息和进度更新
- **WARN**: 警告信息，不影响执行
- **ERROR**: 错误信息，影响执行

**日志内容**：
- 处理步骤和进度
- 配置参数和设置
- 数据质量统计
- 性能指标
- 错误和警告详情

## 性能和扩展性

### 1. 性能优化

**内存管理**：
- 流式数据处理
- 及时释放大对象
- 内存池重用
- 垃圾回收优化

**计算优化**：
- 向量化操作
- 并行计算支持
- 算法复杂度优化
- 缓存机制

**I/O 优化**：
- 批量文件操作
- 压缩格式支持
- 异步I/O
- 内存映射文件

### 2. 扩展性设计

**水平扩展**：
- 支持多进程并行
- 分布式计算接口
- 云计算兼容性

**垂直扩展**：
- 模块化插件架构
- 动态算法加载
- 自定义处理器注册

**数据扩展**：
- 大数据集处理
- 流式数据支持
- 增量处理能力

## 测试架构

### 1. 测试层次

**单元测试**：
- 每个函数的独立测试
- 边界条件测试
- 错误情况测试

**集成测试**：
- 模块间接口测试
- 数据流测试
- 配置集成测试

**端到端测试**：
- 完整工作流程测试
- 真实数据测试
- 性能基准测试

### 2. 测试工具和框架

**测试框架**：
- Test.jl: Julia 标准测试框架
- 自定义测试工具
- 数据生成器
- 基准测试工具

**测试数据**：
- 合成测试数据
- 匿名化真实数据
- 边界测试用例
- 错误场景数据

通过这种架构设计，CleanMast 实现了高度的模块化、可维护性和可扩展性，为风能数据处理提供了一个稳定、可靠的平台基础。
# 开发文档

## 概述

本部分文档面向 CleanMast 项目的开发者和贡献者，提供代码架构、开发规范、测试指南和贡献流程等技术信息。

## 文档结构

### 架构文档 (architecture/)
系统架构和设计模式：

- [总体架构](architecture/overview.md) - 系统高层架构和设计理念
- [模块组织](architecture/modules.md) - 模块结构和依赖关系
- [CLI 结构](architecture/cli-structure.md) - 命令行接口设计
- [数据流](architecture/data-flow.md) - 数据处理流水线

### 贡献指南 (contribution/)
开发环境和贡献流程：

- [开发环境配置](contribution/setup.md) - 开发环境搭建指南
- [编码规范](contribution/coding-standards.md) - Julia 代码风格和规范
- [测试指南](contribution/testing.md) - 测试框架和测试策略
- [添加新功能](contribution/adding-features.md) - 如何添加新命令和模块

### API 文档 (api/)
核心 API 和接口文档：

- [类型系统](api/types.md) - 核心数据类型和结构
- [公共接口](api/interfaces.md) - 模块间接口定义
- [工具函数](api/utilities.md) - 通用工具和辅助函数

### 部署文档 (deployment/)
构建和发布流程：

- [构建指南](deployment/building.md) - 项目构建和打包
- [发布流程](deployment/releases.md) - 版本发布和分发

## 开发原则

### 1. 函数式编程优先
- 优先使用纯函数
- 避免全局状态
- 使用不可变数据结构
- 函数组合和管道操作

### 2. 类型安全
- 明确的类型注解
- 利用 Julia 的类型系统
- 编译时错误检查
- 运行时类型验证

### 3. 模块化设计
- 单一职责原则
- 松耦合高内聚
- 清晰的模块边界
- 可测试的组件

### 4. 可扩展性
- 插件化架构
- 配置驱动
- 抽象接口设计
- 向后兼容性

## 代码组织

### 项目结构
```
src/
├── CleanMastProject.jl      # 主模块入口
├── CleanMastCli.jl         # CLI 命令定义
├── CleanMastUtils.jl       # 通用工具函数
├── Types/                  # 类型定义
│   ├── Utils.jl
│   ├── ParseSensorsConfig.jl
│   └── ...
├── ParseSensors/           # 传感器解析模块
├── DataClean/              # 数据清理模块
├── ReconstructSingleMast/  # 单测风塔重构模块
├── TrainMeso/              # 中尺度训练模块
├── AnalyzeTimeSeries/      # 时间序列分析模块
└── ...
```

### 模块命名规范
- **功能模块**: `FeatureName/` (如 `DataClean/`, `TowerShading/`)
- **类型模块**: `Types/FeatureNameConfig.jl`
- **处理命令**: `FeatureName/ProcessFeatureNameCommand.jl` 或 `FeatureName/CommandFeatureName.jl`
- **推荐命令**: `FeatureName/RecommendFeatureNameCommand.jl`
- **核心算法**: `FeatureName/Core.jl`

### 文件命名规范
- 使用 PascalCase: `DataClean.jl`
- 配置类型: `FeatureNameConfig.jl`
- 处理命令文件: `ProcessFeatureNameCommand.jl` 或 `CommandFeatureName.jl`
- 推荐命令文件: `RecommendFeatureNameCommand.jl`
- 核心算法: `Core.jl`
- 工具函数: `Utils.jl` 或 `Helpers.jl`

### 命令模块结构模式
每个功能模块通常包含以下文件：
```
FeatureName/
├── Core.jl                          # 核心算法实现
├── ProcessFeatureNameCommand.jl     # process 命令实现
├── RecommendFeatureNameCommand.jl   # recommend 命令实现
└── Utils.jl                         # 模块特定工具函数
```

**示例**:
- `DataClean/ProcessCleanCommand.jl` - 实现 `process clean` 命令
- `DataClean/RecommendProcessCleanCommand.jl` - 实现 `recommend process-clean` 命令
- `TowerShading/CommandTowerShading.jl` - 实现 `process tower-shading` 命令
- `TowerShading/RecommendTowerShadingCommand.jl` - 实现 `recommend tower-shading` 命令

## 开发工作流程

### 1. 功能开发流程
```
1. 需求分析和设计
   ↓
2. 创建功能分支
   ↓
3. 编写类型定义
   ↓
4. 实现核心功能
   ↓
5. 添加命令接口
   ↓
6. 编写测试用例
   ↓
7. 编写文档
   ↓
8. 代码审查
   ↓
9. 合并到主分支
```

### 2. 测试策略
- **单元测试**: 每个函数的独立测试
- **集成测试**: 模块间交互测试
- **端到端测试**: 完整工作流程测试
- **性能测试**: 大数据量下的性能验证

### 3. 文档要求
- 每个公共函数必须有文档字符串
- 模块级别的使用说明
- 配置文件格式文档
- 示例代码和用法

## 技术栈

### 核心技术
- **语言**: Julia 1.6+
- **CLI 框架**: Comonicon.jl
- **配置解析**: TOML.jl, YAML.jl
- **数据处理**: DataFrames.jl, CSV.jl
- **统计分析**: Statistics.jl, StatsBase.jl
- **可视化**: PlotlyJS.jl, Plots.jl

### 开发工具
- **版本控制**: Git
- **测试框架**: Test.jl
- **文档生成**: Documenter.jl
- **代码格式**: JuliaFormatter.jl
- **包管理**: Pkg.jl

### 外部依赖
- **数值计算**: LinearAlgebra.jl
- **时间处理**: Dates.jl
- **文件操作**: FileIO.jl
- **序列化**: JLD2.jl
- **HTTP**: HTTP.jl (如果需要)

## 质量保证

### 代码质量标准
- 代码覆盖率 > 80%
- 所有公共函数有测试
- 所有模块有文档
- 通过静态分析检查

### 性能要求
- 内存使用优化
- 大数据集处理能力
- 合理的计算时间
- 可配置的并行处理

### 错误处理
- 详细的错误信息
- 优雅的错误恢复
- 日志记录
- 用户友好的提示

## 发布管理

### 版本控制
- 语义化版本号 (SemVer)
- 主要版本: 不兼容的 API 更改
- 次要版本: 向后兼容的功能添加
- 补丁版本: 向后兼容的错误修复

### 发布检查清单
- [ ] 所有测试通过
- [ ] 文档更新完整
- [ ] 版本号更新
- [ ] 变更日志更新
- [ ] 向后兼容性验证
- [ ] 性能回归测试

### 支持策略
- 最新主要版本: 完全支持
- 上一个主要版本: 错误修复
- 更早版本: 安全修复

## 社区参与

### 贡献方式
- 代码贡献
- 文档改进
- 错误报告
- 功能建议
- 测试和反馈

### 沟通渠道
- GitHub Issues: 错误报告和功能请求
- GitHub Discussions: 技术讨论
- Pull Requests: 代码贡献
- 文档: 使用指南和 API 参考

### 行为准则
- 尊重和包容
- 建设性反馈
- 协作精神
- 技术导向的讨论

## 学习资源

### Julia 语言
- [Julia 官方文档](https://docs.julialang.org/)
- [Julia 性能优化](https://docs.julialang.org/en/v1/manual/performance-tips/)
- [Julia 包开发](https://pkgdocs.julialang.org/)

### 风能相关
- IEC 61400-12-1: 风力发电机功率特性测量
- IEC 61400-1: 风力发电机设计要求
- 大气边界层气象学基础

### 软件工程
- 函数式编程原理
- 测试驱动开发
- 持续集成/持续部署
- 开源项目管理

通过遵循这些开发指南和最佳实践，我们可以确保 CleanMast 项目的代码质量、可维护性和可扩展性，为风能数据处理领域提供一个稳定可靠的工具。
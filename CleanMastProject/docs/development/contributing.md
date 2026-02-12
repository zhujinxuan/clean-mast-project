# 贡献指南

## 概述

欢迎参与 CleanMast 项目贡献！本文档面向开发者，提供开发环境配置、工作流程、代码规范和 Pull Request 流程等指南。CleanMast 是一个用于处理风能测风塔数据的 Julia 工具包，采用函数式编程风格和类型安全设计。

## 开发环境配置

### 环境要求

确保你的开发环境满足以下要求：

- **Julia 版本**: 1.6 或更高版本（推荐 1.11.7）
- **Git**: 用于版本控制
- **编辑器**: VS Code + Julia 插件，或其他支持 Julia 的 IDE

### 项目结构

CleanMast 采用 Julia workspace 结构，根目录 `Project.toml` 定义工作空间成员：

```
clean-mast-project/
├── Project.toml              # Workspace 配置: members = ["CleanMastProject"]
├── bin/
│   └── CleanMast.jl         # 入口脚本，激活 CleanMastProject 环境
└── CleanMastProject/         # 实际的 Julia 包
    ├── Project.toml         # 包依赖和元数据
    ├── src/                 # 源代码
    ├── test/                # 测试套件
    └── docs/               # 文档
```

### 安装步骤

1. 克隆代码仓库到本地目录
2. 安装 Julia 1.6+
3. 在项目根目录启动 Julia REPL，运行以下命令：

```julia
using Pkg
Pkg.activate("CleanMastProject")
Pkg.instantiate()
```

### 运行项目

通过命令行运行 CleanMast：

```bash
julia bin/CleanMast.jl <命令> <选项>
```

### 运行测试

```bash
# 运行所有测试
julia CleanMastProject/test/runtests.jl

# 运行特定测试集
julia CleanMastProject/test/runtests.jl parse_sensors
julia CleanMastProject/test/runtests.jl data-clean process

# 查看可用测试集列表
julia CleanMastProject/test/runtests.jl --help
```

## Git 工作流程

### 分支命名规范

采用语义化分支命名，保持代码库整洁：

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| 功能分支 | `feat/<描述>` | `feat/add-reconstruct-cross` |
| 修复分支 | `fix/<描述>` | `fix/icing-detection-edge-case` |
| 文档分支 | `docs/<描述>` | `docs/update-configuration-guide` |
| 重构分支 | `refactor/<描述>` | `refactor/data-clean-utils` |

### 提交规范

提交信息采用 `组件: 简要描述` 格式，控制在 72 字符以内：

```
# 好的提交信息示例
parse-sensors: 添加 Ch2/Ch7 传感器合并逻辑
data-clean: 修复结冰检测边界条件
tower-shading: 优化塔影校正算法性能
docs: 更新测试文档说明

# 不好的提交信息示例
fix stuff
update
wip
```

### 提交前检查

在创建提交前，确保完成以下检查：

- 所有测试通过
- 代码格式符合项目规范
- 新功能包含对应测试用例
- 文档已同步更新

## 代码规范

### 核心原则

CleanMast 遵循以下核心设计原则，开发时必须严格遵守：

1. **函数式编程优先**：优先使用纯函数，避免全局状态，使用不可变数据结构，通过函数组合和管道操作实现复杂逻辑
2. **类型安全**：使用明确的类型注解，利用 Julia 的类型系统进行编译时错误检查
3. **模块化设计**：遵循单一职责原则，保持模块间松耦合高内聚

### 格式要求

- **缩进**: Julia 代码使用 4 空格
- **行长度**: 最多 92 字符
- **文件路径**: 使用完整绝对路径（Windows: `C:\path\to\file`）

### 函数设计

为提高错误检测能力和代码可维护性，使用严格的类型签名：

```julia
# 正确示例 - 明确的类型注解
function process_wind_data(data::DataFrame, config::ProcessCleanConfig)::DataFrame
    validate_data_format(data)
    return apply_processing_rules(data, config)
end

# 使用显式分号传递关键字参数
Position(; line=1, character=0)
```

### 数据处理规范

处理 DataFrame 时必须注意 Symbol 与 String 的区别：

```julia
# 正确 - 使用 Symbol
select(df, :wind_speed, :wind_direction)
df[:, :timestamp]

# 错误 - 使用 String（会导致错误）
select(df, "wind_speed", "wind_direction")
```

### 函数式编程风格

**禁止**使用 `push!` 等命令式循环模式，必须使用函数式替代方案：

```julia
# 错误 - 命令式风格
results = DataFrame()
for row in eachrow(data)
    if row.wind_speed > threshold
        push!(results, row)
    end
end

# 正确 - 函数式风格
results = filter(row -> row.wind_speed > threshold, data)

# 正确 - 列表推导式
wind_speeds = [s.height for s in sensors if s.sensorType == "WindSpeed"]

# 正确 - 使用 DataFrame 连接而非循环
combined_data = leftjoin(mast_data, meso_data; on = :timestamp)
```

### 模块结构模式

每个功能模块通常包含以下文件结构：

```
FeatureName/
├── Core.jl                          # 核心算法实现
├── ProcessFeatureNameCommand.jl     # process 命令实现
├── RecommendFeatureNameCommand.jl   # recommend 命令实现
└── Utils.jl                         # 模块特定工具函数
```

### 注释策略

- **最少注释原则**：仅在真正必要的地方添加注释
- **自文档化代码**：通过清晰的函数和变量命名替代注释
- **文档字符串**：用于公共 API 函数
- **领域上下文**：仅注释气象假设或物理约束

## 测试要求

### 测试标准

- 所有公共 API 函数必须有测试覆盖
- 代码覆盖率目标不低于 80%
- 关键内部逻辑必须有测试
- 必须测试边界情况和错误路径

### 测试组织

测试遵循与源代码匹配的目录结构：

```
test/
├── runtests.jl                  # 主测试运行器
├── ParseSensors/                # ParseSensors 模块测试
│   ├── fixtures/               # 测试 fixtures
│   ├── test_column_parser.jl
│   └── test_dataframe_processor.jl
├── DataClean/                   # DataClean 模块测试
│   ├── test_range_rules.jl
│   ├── test_icing_rules.jl
│   ├── test_layer_diff_rules.jl
│   └── test_availability_rules.jl
└── ...
```

### 使用 Fixtures

**使用 Fixtures 的场景**：
- 复杂测试场景，包含多个测试用例
- 代表真实场景的黄金测试数据
- 跨多个测试集复用的测试数据
- 过大无法手写的测试数据

**使用内联/临时数据的场景**：
- 包含少量数据的简单单元测试
- 文件 I/O 测试（应使用 `mktempdir()`）
- 构建完整环境的集成测试

### 常见陷阱

1. **DataFrame 列名类型**: `names(df)` 返回 **String**，不是 **Symbol**
2. **Symbol 构造**: 不能在 DataFrame 构造函数中直接使用 `Symbol()`
3. **路径转义**: Bash 命令中的路径必须使用正斜杠 `/` 或双反斜杠 `\\`

## Pull Request 流程

### 创建 PR 前

1. **代码完成**: 确保所有功能实现完毕，代码整洁
2. **测试通过**: 运行相关测试集，确认所有测试通过
3. **代码格式**: 运行代码格式化工具（JuliaFormatter.jl）
4. **文档更新**: 更新相关文档和使用说明
5. **冲突解决**: 同步最新主分支，解决合并冲突

### PR 内容要求

- **标题**: 清晰描述 PR 目的，如 `feat: 添加跨测风塔重构功能`
- **描述**: 详细说明变更内容、动机和测试方法
- **关联 Issue**: 关联相关的问题编号（如果有）
- **截图**: 对于 UI 变更，添加截图或 GIF

### PR 审查流程

1. 提交 PR 后，等待维护者审查
2. 根据审查意见进行代码修改
3. 审查通过后，维护者将合并到主分支
4. PR 合并后，删除源分支

### 代码审查标准

审查时关注以下方面：

- **正确性**: 代码是否正确实现了需求？
- **完整性**: 是否覆盖所有边界情况？
- **可读性**: 代码是否清晰易懂？
- **性能**: 是否有性能问题？
- **测试**: 测试是否充分？
- **文档**: 文档是否同步更新？

## 文档要求

### 文档位置

- **用户文档**: `docs/user/` - 面向最终用户的使用指南
- **技术文档**: `docs/technical/` - 算法实现细节
- **开发文档**: `docs/development/` - 面向开发者的技术文档

### 文档标准

- **中文语言**: `docs/` 下所有文档使用中文
- **简洁格式**: 保持文档简洁聚焦
- **实用示例**: 提供真实的配置示例
- **源文件约束**: 仅基于实际代码文件编写文档

### 需要更新的文档

- 新增功能需添加使用说明
- 配置文件变更需更新配置文档
- API 变更需更新接口文档
- 重大变更需更新 README

## 问题报告指南

### 报告问题

通过 GitHub Issues 报告问题：

1. **使用模板**: 优先使用问题模板
2. **描述清晰**: 说明问题现象、复现步骤和期望行为
3. **提供信息**: 附加错误日志、配置文件和数据样本（脱敏后）
4. **搜索先例**: 确认是否为已知问题

### 功能请求

提交功能请求时：

1. **说明场景**: 描述使用场景和需求动机
2. **提供方案**: 建议的实现方案或 API 设计
3. **参考现有**: 参考现有类似功能的实现方式
4. **优先级**: 说明功能的优先级和使用频率

## 相关文档

- [开发文档主页](README.md) - 开发文档入口
- [测试指南](tests.md) - 详细测试规范
- [代码风格指南](code-style/julia-guide.md) - Julia 代码风格
- [文档导航中心](../../README.md) - 所有文档入口

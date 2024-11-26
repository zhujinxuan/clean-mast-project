# 文件：./src/CleanMast.jl

using ArgParse
include("./CleanMastConfig.jl")
using .CleanMastConfig
using .MastTimeSeries

# 主函数：解析命令行参数并调用相应的功能
function main()
    args = Base.ARGS
    command, dir = parse_arguments(args)

    # 根据命令调用相应的函数
    if command == "check:config"
        check_config(dir)
    elseif command == "check:sensors"
        check_sensors(dir)
    else
        error("无效的命令: $command")
    end
end

# 解析命令行参数
function parse_arguments(args::Vector{String})
    s = ArgParseSettings()
    @add_arg_table! s begin
        "command"
        help = "要执行的命令，如 check:config, check:sensors"
        arg_type = String
        required = true

        "--dir"
        help = "指定配置文件所在的目录"
        arg_type = String
        required = true
    end
    parsed_args = parse_args(args, s)
    command = parsed_args["command"]
    return command, get(parsed_args, "dir", "")
end

# 检查配置文件是否存在并尝试解析
function check_config(dir::String)
    config_path = joinpath(dir, "config.yaml")
    if isdir(dir) && isfile(config_path)
        println("目录和配置文件存在: $config_path")
        # 尝试解析配置文件
        try
            CleanMastConfig.parse_config(dir)
            println("配置文件解析成功")
        catch e
            error("配置文件解析失败: $(e.message)")
        end
    else
        error("指定的目录无效或配置文件不存在: $config_path")
    end
end

# 读取MAST数据并生成sensors.yaml
function check_sensors(dir::String)
    # 首先确保配置文件存在并可以解析
    config_path = joinpath(dir, "config.yaml")
    if !isdir(dir) || !isfile(config_path)
        error("指定的目录无效或配置文件不存在: $config_path")
    end

    try
        # 解析配置
        config = CleanMastConfig.parse_config(dir)
        println("配置文件解析成功")

        # 读取MAST数据
        println("开始读取MAST数据...")
        time_series = read_mast_data(config, dir)
        
        # 如果成功，打印结果
        n_sensors = length(time_series.sensors)
        println("成功解析 $n_sensors 个传感器")
        
        # 打印每个传感器的基本信息
        for (i, sensor) in enumerate(time_series.sensors)
            println("传感器 $i:")
            println("  列名: $(sensor.columnName)")
            println("  类型: $(sensor.sensorType)")
            println("  高度: $(sensor.height)m")
            println("  方向: $(sensor.sensorDirection)")
            println("  统计类型: $(sensor.statType)")
        end

        println("处理完成，详细信息已保存到 sensors.yaml")
        
    catch e
        error("处理失败: $(e.message)")
    end
end

# 执行主函数
if abspath(PROGRAM_FILE) == @__FILE__
    main()
end

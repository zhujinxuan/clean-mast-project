module CheckSensors

using ....Types.CleanMastConfig
using ....MastTimeSeries

export execute

function execute(dir::String)
    config_path = joinpath(dir, "config.yaml")
    if !isdir(dir) || !isfile(config_path)
        error("指定的目录无效或配置文件不存在: $config_path")
    end

    try
        config = CleanMastConfig.parse_config(dir)
        println("配置文件解析成功")

        println("开始读取MAST数据...")
        time_series = read_mast_data(config, dir)
        
        n_sensors = length(time_series.sensors)
        println("成功解析 $n_sensors 个传感器")
        
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

end 
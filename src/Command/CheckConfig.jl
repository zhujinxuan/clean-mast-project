module CheckConfig

using ...CleanMastConfig

function execute(dir::String)
    config_path = joinpath(dir, "config.yaml")
    if isdir(dir) && isfile(config_path)
        println("目录和配置文件存在: $config_path")
        # 尝试解析配置文件
        try
            parse_config(dir)
            println("配置文件解析成功")
        catch e
            error("配置文件解析失败: $(e.message)")
        end
    else
        error("指定的目录无效或配置文件不存在: $config_path")
    end
end

export execute
end 
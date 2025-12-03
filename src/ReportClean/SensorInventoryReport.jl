module SensorInventoryReport

using DataFrames
using ....Types.ReportCleanData: MastReportData
using ....Types.SensorColumns: SensorColumn, create_sensor_short_name

export generate_sensor_inventory_section

"""
    generate_sensor_inventory_section(mast_data::Vector{MastReportData}) :: String

Generate sensor inventory section for the report.
Shows unique sensors organized by mast, grouped by sensor type.
Only considers sensors with statType = 'avg'.
Two columns: 传感器类型 and 位置.
"""
function generate_sensor_inventory_section(mast_data::Vector{MastReportData}) :: String
    if isempty(mast_data)
        return "== 传感器清单\n\n未找到测风塔数据。\n"
    end

    # Generate report sections
    sections = String[
        "== 传感器清单",
        "",
        "本节列出各测风塔的传感器配置信息，按传感器类型分组。",
        ""
    ]

    # Process each mast separately
    for mast in mast_data
        # Add mast header
        push!(sections, "=== $(mast.name)")
        push!(sections, "")

        # Filter only avg sensors and get unique sensors by type, height, direction
        unique_sensors = Dict{Tuple{String, Float64, String}, SensorColumn}()
        for sensor in mast.raw_data.sensors
            if sensor.statType == "avg"
                key = (sensor.sensorType, sensor.height, sensor.sensorDirection)
                if !haskey(unique_sensors, key)
                    unique_sensors[key] = sensor
                end
            end
        end

        # Convert to vector and sort by type, height, direction
        sensors = collect(values(unique_sensors))
        sort!(sensors, by = s -> (s.sensorType, s.height, s.sensorDirection))

        # Group sensors by type
        sensor_groups = Dict{String, Vector{SensorColumn}}()
        for sensor in sensors
            sensor_type_cn = translate_sensor_type(sensor.sensorType, sensor.columnName)
            if !haskey(sensor_groups, sensor_type_cn)
                sensor_groups[sensor_type_cn] = SensorColumn[]
            end
            push!(sensor_groups[sensor_type_cn], sensor)
        end

        # Sort sensor types for consistent ordering
        sorted_types = sort(collect(keys(sensor_groups)))

        # Create table with two columns
        push!(sections, "#table(")
        push!(sections, "  columns: 2,")
        push!(sections, "  [传感器类型], [位置],")

        # Add sensors grouped by type
        for sensor_type_cn in sorted_types
            type_sensors = sensor_groups[sensor_type_cn]

            # Check if there are multiple sensors at the same height
            height_counts = Dict{Float64, Int}()
            for sensor in type_sensors
                height_counts[sensor.height] = get(height_counts, sensor.height, 0) + 1
            end

            # Build position string
            positions = String[]
            for sensor in type_sensors
                if height_counts[sensor.height] > 1
                    # Multiple sensors at same height, include direction
                    height_str = sensor.height == floor(sensor.height) ?
                        string(Int(sensor.height)) : string(sensor.height)
                    direction_str = sensor.sensorDirection == "N/A" ? "" : ":$(sensor.sensorDirection)"
                    push!(positions, "$(height_str)m$(direction_str)")
                else
                    # Single sensor at this height
                    height_str = sensor.height == floor(sensor.height) ?
                        string(Int(sensor.height)) : string(sensor.height)
                    push!(positions, "$(height_str)m")
                end
            end

            position_str = join(positions, ", ")
            push!(sections, "  [$sensor_type_cn], [$position_str],")
        end

        push!(sections, ")")
        push!(sections, "")
    end

    return join(sections, "\n")
end

"""
Translate sensor type to Chinese.
"""
function translate_sensor_type(sensor_type::String, column_name::Symbol)::String
    if sensor_type == "WindSpeed"
        return "风速"
    elseif sensor_type == "WindDirection"
        return "风向"
    elseif sensor_type == "Temperature"
        return "温度"
    elseif sensor_type == "Pressure"
        return "气压"
    elseif sensor_type == "Analog"
        # Check column name for analog sensors
        col_name = string(column_name)
        if occursin("Pres", col_name) || occursin("kPa", col_name)
            return "气压"
        elseif occursin("RH", col_name) || occursin("%RH", col_name)
            return "相对湿度"
        else
            return "模拟量"
        end
    else
        return sensor_type
    end
end

end # module SensorInventoryReport

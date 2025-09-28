module SensorInventoryReport

using DataFrames
using ....Types.ReportCleanData: MastReportData
using ....Types.SensorColumns: SensorColumn, create_sensor_short_name

export generate_sensor_inventory_section

"""
    generate_sensor_inventory_section(mast_data::Vector{MastReportData}) :: String

Generate sensor inventory section for the report.
Shows unique sensors organized by mast, then by sensor type, height, and direction.
Only shows base sensors (not statistical channels like avg, sd, min, max).
"""
function generate_sensor_inventory_section(mast_data::Vector{MastReportData}) :: String
    if isempty(mast_data)
        return "== 传感器清单\n\n未找到测风塔数据。\n"
    end

    # Generate report sections
    sections = String[
        "== 2. 传感器清单",
        "",
        "本节列出各测风塔的传感器配置信息，按传感器类型、高度和方向排序。",
        ""
    ]

    # Process each mast separately
    for mast in mast_data
        # Add mast header
        push!(sections, "=== $(mast.name)")
        push!(sections, "")

        # Get unique sensors (group by sensorType, height, sensorDirection)
        unique_sensors = Dict{Tuple{String, Float64, String}, SensorColumn}()
        for sensor in mast.raw_data.sensors
            key = (sensor.sensorType, sensor.height, sensor.sensorDirection)
            if !haskey(unique_sensors, key)
                unique_sensors[key] = sensor
            end
        end

        # Convert to vector and sort by type, height, direction
        sensors = collect(values(unique_sensors))
        sort!(sensors, by = s -> (s.sensorType, s.height, s.sensorDirection))

        # Group sensors by type
        sensor_groups = Dict{String, Vector{SensorColumn}}()
        for sensor in sensors
            if !haskey(sensor_groups, sensor.sensorType)
                sensor_groups[sensor.sensorType] = SensorColumn[]
            end
            push!(sensor_groups[sensor.sensorType], sensor)
        end

        # Create one table for all sensors in this mast
        push!(sections, "#table(")
        push!(sections, "  columns: 3,")
        push!(sections, "  [传感器名称], [传感器数据类型], [高度 (m)],")

        # Add all sensors to one table, sorted by type, height, direction
        for sensor in sensors
            # Use Typst-compatible sensor short name
            sensor_name = create_sensor_short_name(sensor)

            # Translate sensor type to Chinese
            sensor_data_type = if sensor.sensorType == "WindSpeed"
                "风速"
            elseif sensor.sensorType == "WindDirection"
                "风向"
            elseif sensor.sensorType == "Temperature"
                "温度"
            elseif sensor.sensorType == "Analog"
                # Check if it's pressure or humidity based on column name
                col_name = string(sensor.columnName)
                if occursin("Pres", col_name) || occursin("kPa", col_name)
                    "气压"
                elseif occursin("RH", col_name) || occursin("%RH", col_name)
                    "湿度"
                else
                    "模拟量"
                end
            else
                sensor.sensorType
            end

            height = string(Int(sensor.height))

            push!(sections, "  [$sensor_name], [$sensor_data_type], [$height],")
        end

        push!(sections, ")")
        push!(sections, "")
    end

    return join(sections, "\n")
end

end # module SensorInventoryReport

module Turbulence

using DataFrames
using CSV
using AlgebraOfGraphics
using CairoMakie
using Statistics
using Dates
using SummaryTables

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
import ...Types.ReportTimeSeriesConfiguration: ReportTimeSeriesConfig, MastReportTimeSeriesConfig, get_output_path
import ...Types.Sector: DIRECTION_16_SECTORS, get_direction_sector
import ...Types.TurbulenceIntensity: TurbulenceSectorStats, TurbulenceResults
import ..Utils: format_height

const DEFAULT_WIND_SPEED_BINS = collect(0.0:1.0:28.0)

# IEC 61400-1 turbulence intensity reference values
const IEC_TURBULENCE_CATEGORIES = Dict(
    "A" => 0.16,  # High turbulence
    "B" => 0.14,  # Medium turbulence  
    "C" => 0.12   # Low turbulence
)

"""
Calculate IEC turbulence intensity for a given wind speed and category

# Arguments
- `wind_speed::Float64`: Wind speed in m/s
- `i_ref::Float64`: Reference turbulence intensity for the IEC category

# Returns
- `Float64`: IEC turbulence intensity at the given wind speed
"""
function calculate_iec_ti(wind_speed::Float64, i_ref::Float64)::Float64
    # IEC 61400-1 formula: TI = I_ref * (0.75 + 5.6/V)
    # where V is wind speed in m/s
    wind_speed <= 0.0 && return 0.0
    return i_ref * (0.75 + 5.6 / wind_speed)
end

"""
Determine IEC turbulence category based on representative TI (P90)

# Arguments
- `representative_ti::Float64`: Representative turbulence intensity (P90: mean + 1.28*std)
- `wind_speed::Float64`: Wind speed in m/s

# Returns
- `String`: IEC category ("A+", "A", "B", "C")
"""
function get_iec_category(representative_ti::Float64, wind_speed::Float64)::String
    # Calculate IEC TI for each category at this wind speed
    ti_a = calculate_iec_ti(wind_speed, IEC_TURBULENCE_CATEGORIES["A"])
    ti_b = calculate_iec_ti(wind_speed, IEC_TURBULENCE_CATEGORIES["B"])
    ti_c = calculate_iec_ti(wind_speed, IEC_TURBULENCE_CATEGORIES["C"])
    
    # Determine category based on representative TI
    if representative_ti > ti_a
        return "A+"
    elseif representative_ti > ti_b
        return "A"
    elseif representative_ti > ti_c
        return "B"
    else
        return "C"
    end
end

"""
Find wind speed (avg, std) and direction sensors at the target height
"""
function find_ti_sensors(ts::TimeSeriesData, target_height::Float64)::Tuple{Union{SensorColumn,Nothing}, Union{SensorColumn,Nothing}, Union{SensorColumn,Nothing}}
    # Find average wind speed sensor
    ws_avg = find_nearest_height_sensor(target_height, ts.sensors, "WindSpeed", "avg")
    # Find standard deviation wind speed sensor at the same height as avg
    ws_sd = ws_avg === nothing ? nothing : 
        find_nearest_height_sensor(ws_avg.height, ts.sensors, "WindSpeed", "sd")
    # Find wind direction sensor
    wd = find_nearest_height_sensor(target_height, ts.sensors, "WindDirection", "avg")
    
    return ws_avg, ws_sd, wd
end

"""
Calculate turbulence intensity for each time step
"""
function calculate_ti_series(
    df::DataFrame,
    ws_col::Symbol,
    sd_col::Symbol,
    wd_col::Symbol
)::DataFrame
    # Create result DataFrame with all necessary columns
    result = DataFrame(
        ws_avg = df[!, ws_col],
        ws_sd = df[!, sd_col],
        wd = df[!, wd_col]
    )
    
    # Calculate TI, ensuring minimum wind speed of 1.0 m/s
    result.ti = result.ws_sd ./ map(ws -> max(ws, 1.0), result.ws_avg)
    
    # Add sector for each direction, propagating missing values
    result.sector = map(result.wd) do wd
        ismissing(wd) ? missing : get_direction_sector(wd, DIRECTION_16_SECTORS).name
    end
    
    return result
end

"""
Calculate sector statistics for turbulence intensity
"""
function calculate_sector_stats(ti_df::DataFrame)::TurbulenceSectorStats
    # Filter out rows with missing sectors or missing TI
    valid_data = filter(row -> !ismissing(row.sector) && !ismissing(row.ti), ti_df)
    # Calculate sector statistics
    sector_stats = combine(
        groupby(valid_data, :sector),
        :ws_avg => mean => :mean_speed,
        :ti => mean => :ti,
        :ti => std => :std,
        nrow => :occurrence;
        threads=false
    )
    
    # Calculate overall statistics
    mean_ti = mean(skipmissing(ti_df.ti))
    std_ti = std(skipmissing(ti_df.ti))
    representative_ti = mean_ti + 1.28* std_ti
    
    return TurbulenceSectorStats(sector_stats, mean_ti, std_ti, representative_ti)
end

"""
Calculate turbulence intensity matrix for Meteodyn WT
"""
function calculate_ti_matrix(
    ti_df::DataFrame,
    wind_speed_bins::Vector{Float64},
    mean_ti::Float64
)::DataFrame
    # Create base DataFrame with speed bins
    result = DataFrame(
        v_min = wind_speed_bins[1:end-1],
        v_max = wind_speed_bins[2:end]
    )
    
    # Initialize sector columns with mean TI
    for sector in DIRECTION_16_SECTORS
        result[!, sector.name] = fill(mean_ti, length(wind_speed_bins)-1)
    end
    
    # Calculate TI for each bin and sector
    for (i, (min_speed, max_speed)) in enumerate(zip(wind_speed_bins[1:end-1], wind_speed_bins[2:end]))
        # Get data for this speed bin, skipping missing values
        speed_bin_data = filter(row -> !ismissing(row.ws_avg) && min_speed ≤ row.ws_avg < max_speed, ti_df)
        
        # Calculate TI for each sector with enough data
        for sector in DIRECTION_16_SECTORS
            # Filter for this sector, skipping missing sectors
            sector_data = filter(row -> !ismissing(row.sector) && row.sector == sector.name, speed_bin_data)

            # Count valid TI values and check if we have enough valid data
            valid_count = count(!ismissing, sector_data.ti)
            if valid_count ≥ 5  # Minimum sample size for reliable statistics
                result[i, sector.name] = mean(skipmissing(sector_data.ti))
            end
        end
    end
    
    return result
end

"""
Calculate turbulence intensity statistics by wind speed bin
"""
function calculate_ti_by_wind_speed(
    ti_df::DataFrame,
    wind_speed_bins::Vector{Float64}
)::DataFrame
    # Create empty result DataFrame
    result = DataFrame(
        wind_speed_min = Float64[],
        wind_speed_max = Float64[],
        mean_ti = Float64[],
        std_ti = Float64[],
        occurrence = Int[],
        representative_ti = Float64[],
        iec_category = String[]
    )
    
    # Calculate stats for each wind speed bin
    for (i, (min_speed, max_speed)) in enumerate(zip(wind_speed_bins[1:end-1], wind_speed_bins[2:end]))
        # Filter data for this wind speed bin
        bin_data = filter(row -> !ismissing(row.ws_avg) && min_speed ≤ row.ws_avg < max_speed, ti_df)
        
        # Skip bins with no data
        if nrow(bin_data) == 0
            continue
        end
        
        # Calculate statistics
        bin_mean_ti = mean(skipmissing(bin_data.ti))
        bin_std_ti = nrow(bin_data) > 1 ? std(skipmissing(bin_data.ti)) : 0.0
        bin_representative_ti = bin_mean_ti + 1.28 * bin_std_ti
        
        # Determine IEC category using bin center wind speed
        bin_center_speed = (min_speed + max_speed) / 2.0
        iec_category = get_iec_category(bin_representative_ti, bin_center_speed)
        
        # Add row to results
        push!(result, (
            min_speed,
            max_speed,
            bin_mean_ti,
            bin_std_ti,
            nrow(bin_data),
            bin_representative_ti,
            iec_category
        ))
    end
    
    return result
end

"""
Calculate sector statistics for turbulence intensity with optional wind speed filtering
"""
function calculate_filtered_sector_stats(
    ti_df::DataFrame;
    min_ws::Union{Nothing, Float64} = nothing,
    max_ws::Union{Nothing, Float64} = nothing
)::TurbulenceSectorStats
    # Apply wind speed filtering if requested
    filtered_df = ti_df
    if !isnothing(min_ws) || !isnothing(max_ws)
        filtered_df = filter(row -> begin
            # Skip missing wind speeds
            ismissing(row.ws_avg) && return false
            
            # Apply min filter if specified
            if !isnothing(min_ws) && row.ws_avg < min_ws
                return false
            end
            
            # Apply max filter if specified
            if !isnothing(max_ws) && row.ws_avg > max_ws
                return false
            end
            
            return true
        end, ti_df)
    end
    
    # Now use the standard sector stats calculation on filtered data
    return calculate_sector_stats(filtered_df)
end

"""
Process turbulence intensity for a single height
"""
function process_turbulence_intensity(
    ts::TimeSeriesData,
    target_height::Float64,
    wind_speed_bins::Vector{Float64}
)::TurbulenceResults
    # Find required sensors
    ws_avg, ws_sd, wd = find_ti_sensors(ts, target_height)
    
    isnothing(ws_avg) && error("No wind speed sensor found near height $(target_height)m")
    isnothing(ws_sd) && error("No wind speed standard deviation sensor found at height $(ws_avg.height)m")
    isnothing(wd) && error("No wind direction sensor found near height $(target_height)m")
    
    # Calculate TI time series
    ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
    
    # Calculate sector statistics
    sector_stats = calculate_sector_stats(ti_df)
    
    # Calculate TI matrix for Meteodyn WT
    ti_matrix = calculate_ti_matrix(ti_df, wind_speed_bins, sector_stats.mean_ti)
    
    return TurbulenceResults(ti_df, sector_stats, ti_matrix)
end

"""
Save Meteodyn WT turbulence intensity file
"""
function save_meteodyn_ti(output_dir::String, ti_matrix::DataFrame, height::Float64)
    meteodyn_path = joinpath(output_dir, "meteodyn_ti_$(height)m.txt")
    
    open(meteodyn_path, "w") do io
        println(io, nrow(ti_matrix))
        for row in eachrow(ti_matrix)
            values = [row.v_max]
            append!(values, [row[sector.name] for sector in DIRECTION_16_SECTORS])
            println(io, join(values, "\t"))
        end
    end
    
    @info "Saved Meteodyn WT file: $meteodyn_path"
end

"""
Create combined turbulence intensity comparison plot for multiple heights

# Arguments
- `mast_name::String`: Name of the mast
- `heights::Vector{Float64}`: Heights to include (only >= min_plot_height)
- `output_dir::String`: Directory containing CSV files and where to save the plot
- `min_plot_height::Float64`: Minimum height threshold for plotting (default: 100.0)

# Description
Creates a single plot showing:
- Representative TI values from all heights >= min_plot_height as lines
- IEC Category A, B, C standard curves as filled bands
- Only includes wind speeds >= 1 m/s
"""
function create_combined_ti_comparison_plot(
    mast_name::String,
    heights::Vector{Float64},
    output_dir::String,
    min_plot_height::Float64 = 100.0
)::Nothing
    # Filter heights >= min_plot_height
    plot_heights = filter(h -> h >= min_plot_height, heights)
    sort!(plot_heights, rev=true)

    if isempty(plot_heights)
        @warn "No heights >= $(min_plot_height)m found for plotting"
        return nothing
    end
    
    all_meas_datas = map(plot_heights) do height
        ti_by_ws_path = joinpath(output_dir, "ti_by_wind_speed_$(height)m.csv")
        
        if !isfile(ti_by_ws_path)
            @warn "TI by wind speed file not found for height $(height)m"
            return DataFrame(wind_speed = Float64[], ti = Float64[], category = String[])
        end
        
        # Read data
        ti_by_ws_df = CSV.read(ti_by_ws_path, DataFrame)
        
        # Filter for wind speeds >= 1 m/s
        plot_data = filter(row -> row.wind_speed_min >= 1.0, ti_by_ws_df)
        
        # Calculate wind speed centers
        plot_data.wind_speed_center = (plot_data.wind_speed_min .+ plot_data.wind_speed_max) ./ 2.0
        
        # Add to combined data
        return DataFrame(
            wind_speed = plot_data.wind_speed_center,
            ti = plot_data.representative_ti,
            category = "Spd $(format_height(height))m"
        )
    end

    
    if isempty(all_meas_datas)
        @warn "No measurement data found for heights >= $(min_plot_height)m"
        return nothing
    end

    all_meas_data = vcat(all_meas_datas...)
    
    # Create IEC standard curves for bands
    wind_speeds = collect(1.0:0.1:30.0)
    ti_a = [calculate_iec_ti(ws, IEC_TURBULENCE_CATEGORIES["A"]) for ws in wind_speeds]
    ti_b = [calculate_iec_ti(ws, IEC_TURBULENCE_CATEGORIES["B"]) for ws in wind_speeds]
    ti_c = [calculate_iec_ti(ws, IEC_TURBULENCE_CATEGORIES["C"]) for ws in wind_speeds]
    
    # Create IEC band data for linesfill
    iec_band_data = vcat(
    # IEC Category A (between A and B)
    DataFrame(
        wind_speed = wind_speeds,
        lower = ti_b,
        upper = ti_a,
        category = "IEC Category A"
    ),
    # IEC Category B (between B and C)
    DataFrame(
        wind_speed = wind_speeds,
        lower = ti_c,
        upper = ti_b,
        category = "IEC Category B"
    ),
    # IEC Category C (below Category C)
    DataFrame(
        wind_speed = wind_speeds,
        lower = 0.0,
        upper = ti_c,
        category = "IEC Category C"
    ))

    # Create IEC bands using linesfill with their own color scale
    iec_bands = data(iec_band_data) * 
        mapping(:wind_speed, :upper, lower=:lower, color=:category => presorted => "IEC Categories") * 
        visual(LinesFill, fillalpha=0.4, linewidth=0)
    
    # Create measurement lines with their own color scale
    meas_lines = data(all_meas_data) * 
        mapping(:wind_speed, :ti, color=:category => presorted => "Measurement Heights") *
        visual(Lines, linewidth=2) 
    
    # Combine layers
    combined_plot = iec_bands + meas_lines
    
    # Draw the combined plot
    fig = draw(combined_plot,
        axis=(
            title="Turbulence Intensity, $mast_name",
            xlabel="Wind Speed (m/s)",
            ylabel="Turbulence Intensity", 
            limits=(0, 30, 0, 1.0),
            yticks=0:0.2:1.0
        ),
        figure=(size=(800, 600),)
    )
    
    # Save the plot
    plot_path = joinpath(output_dir, "iec_comparison_combined.png")
    save(plot_path, fig, px_per_unit=2)

    @info "Saved combined TI comparison plot: $plot_path"
    return nothing
end

"""
    analyze_turbulence_intensity(config::ReportTimeSeriesConfig)

Analyze turbulence intensity for all masts and heights in the configuration.
"""
function analyze_turbulence_intensity(config::ReportTimeSeriesConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "turbulence")
        
        # Find all unique heights with both wind speed avg and sd sensors
        ws_avg_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", 
                               mast.timeSeriesData.sensors)
        ws_sd_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "sd", 
                              mast.timeSeriesData.sensors)
        
        # Get heights that have both avg and sd sensors
        avg_heights = Set([s.height for s in ws_avg_sensors])
        sd_heights = Set([s.height for s in ws_sd_sensors])
        valid_heights = sort(collect(intersect(avg_heights, sd_heights)))
        
        if isempty(valid_heights)
            @warn "No heights with both wind speed avg and sd sensors for mast $(mast.name)"
            continue
        end
        
        mast_results = Dict{String, Any}()
        
        for height in valid_heights
            @info "Processing turbulence intensity for mast $(mast.name) at $(height)m"

            # Process turbulence intensity
            ti_results = process_turbulence_intensity(
                mast.timeSeriesData,
                height,
                DEFAULT_WIND_SPEED_BINS
            )

            # Save sector statistics
            ti_stats_df = select(
                ti_results.sector_stats.sector_stats,
                :sector,
                :mean_speed => :mean_speed,
                :ti => :mean_ti,
                :std => :ti_std,
                :occurrence
            )
            CSV.write(joinpath(output_dir, "turbulence_intensity_$(height)m.csv"), ti_stats_df)

            # Save TI by wind speed
            ti_by_ws = calculate_ti_by_wind_speed(ti_results.time_series, DEFAULT_WIND_SPEED_BINS)
            CSV.write(joinpath(output_dir, "ti_by_wind_speed_$(height)m.csv"), ti_by_ws)

            # Calculate TI for different wind speed ranges
            all_speeds_ti = ti_results.sector_stats.mean_ti
            all_speeds_rep_ti = ti_results.sector_stats.representative_ti
            all_speeds_std_ti = ti_results.sector_stats.std_ti

            # Wind speeds > 3 m/s
            above_3_stats = calculate_filtered_sector_stats(ti_results.time_series, min_ws=3.0)

            # Wind speeds between 14.5 and 16.5 m/s
            ws_14_5_16_5_stats = calculate_filtered_sector_stats(ti_results.time_series, min_ws=14.5, max_ws=16.5)

            # Wind speeds between 9.5 and 10.5 m/s
            ws_9_5_10_5_stats = calculate_filtered_sector_stats(ti_results.time_series, min_ws=9.5, max_ws=10.5)

            # Create report
            report_df = DataFrame(
                mast=[mast.name, mast.name, mast.name, mast.name],
                height=[height, height, height, height],
                wind_speed_range=["all", ">3 m/s", "14.5-16.5 m/s", "9.5-10.5 m/s"],
                mean_ti=[
                    all_speeds_ti,
                    above_3_stats.mean_ti,
                    ws_14_5_16_5_stats.mean_ti,
                    ws_9_5_10_5_stats.mean_ti
                ],
                representative_ti=[
                    all_speeds_rep_ti,
                    above_3_stats.representative_ti,
                    ws_14_5_16_5_stats.representative_ti,
                    ws_9_5_10_5_stats.representative_ti
                ],
                ti_std=[
                    all_speeds_std_ti,
                    above_3_stats.std_ti,
                    ws_14_5_16_5_stats.std_ti,
                    ws_9_5_10_5_stats.std_ti
                ]
            )

            CSV.write(joinpath(output_dir, "turbulence_intensity_report_$(height)m.csv"), report_df)

            # Save Meteodyn WT file
            save_meteodyn_ti(output_dir, ti_results.matrix, height)

            mast_results["$(height)m"] = ti_results

        end
        
        # Create combined TI comparison plot for this mast
        create_combined_ti_comparison_plot(mast.name, valid_heights, output_dir, config.min_plot_height)

        results[mast.name] = mast_results
    end

    return results
end

"""
    analyze_all_turbulence(config::ReportTimeSeriesConfig)

Run all turbulence intensity analyses for all masts in the configuration.
"""
function analyze_all_turbulence(config::ReportTimeSeriesConfig)
    results = analyze_turbulence_intensity(config)
    generate_turbulence_typst_reports(config)
    return results
end

"""
Generate Typst reports with turbulence intensity analysis results for all masts

# Arguments
- `config::ReportTimeSeriesConfig`: Analysis configuration

# Description
Generates a comprehensive Typst report for each mast including all heights:
- Sector statistics tables for each height
- TI by wind speed tables for each height
- Summary report with different wind speed ranges for each height
- All content in Chinese in a single turbulence.typ file
"""
function generate_turbulence_typst_reports(config::ReportTimeSeriesConfig)
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "turbulence")
        
        # Find all unique heights with both wind speed avg and sd sensors
        ws_avg_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", 
                               mast.timeSeriesData.sensors)
        ws_sd_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "sd", 
                              mast.timeSeriesData.sensors)
        
        # Get heights that have both avg and sd sensors
        avg_heights = Set([s.height for s in ws_avg_sensors])
        sd_heights = Set([s.height for s in ws_sd_sensors])
        valid_heights = sort(collect(intersect(avg_heights, sd_heights)))
        valid_heights = filter(h -> h >= config.min_plot_height, valid_heights)
        
        if isempty(valid_heights)
            continue
        end
        
        generate_consolidated_turbulence_typst_report(output_dir, valid_heights, mast.name, config.min_plot_height)
    end
end

"""
Generate a consolidated Typst report with turbulence intensity analysis results for all heights

# Arguments
- `output_dir::String`: Directory containing CSV files and where to save the .typ report
- `heights::Vector{Float64}`: All heights to include in the report
- `mast_name::String`: Name of the mast

# Description
Generates a comprehensive Typst report including all heights:
- Sector statistics tables for each height
- TI by wind speed tables for each height  
- Summary report with different wind speed ranges for each height
- All content in Chinese in a single turbulence.typ file
"""
function generate_consolidated_turbulence_typst_report(
    output_dir::String,
    heights::Vector{Float64},
    mast_name::String,
    min_plot_height::Float64
)::Nothing
    typst_path = joinpath(output_dir, "turbulence.typ")
    
    # Helper function to format data and create table
    function prepare_and_format_table(df::DataFrame, table_type::String)
        formatted_df = copy(df)
        
        if table_type == "sector"
            # Format numeric columns
            for col in names(formatted_df)
                if col == "occurrence"
                    continue
                elseif col in ["mean_speed", "mean_ti", "ti_std"]
                    formatted_values = [ismissing(v) ? "-" : string(round(v, digits=3)) 
                                      for v in formatted_df[!, col]]
                    formatted_df[!, col] = formatted_values
                end
            end
            
            sector_cols = [
                :sector => "风向扇区",
                :mean_speed => "平均风速 (m/s)",
                :mean_ti => "平均湍流强度",
                :ti_std => "湍流强度标准差",
                :occurrence => "数据点数"
            ]
            rename!(formatted_df, sector_cols...)
            
        elseif table_type == "wind_speed"
            # Format wind speed range as string
            formatted_df[!, :wind_speed_range] = map(eachrow(formatted_df)) do row
                "$(Int(row.wind_speed_min))-$(Int(row.wind_speed_max))"
            end
            
            # Format numeric columns
            for col in names(formatted_df)
                if col in ["occurrence", "wind_speed_range", "iec_category"]
                    continue
                elseif col in ["mean_ti", "std_ti", "representative_ti"]
                    formatted_values = [ismissing(v) ? "-" : string(round(v, digits=3)) 
                                      for v in formatted_df[!, col]]
                    formatted_df[!, col] = formatted_values
                end
            end
            
            # Select and reorder columns (include IEC category if it exists)
            if "iec_category" in names(formatted_df)
                formatted_df = select(formatted_df, 
                    :wind_speed_range, :mean_ti, :std_ti, :representative_ti, :iec_category, :occurrence)
            else
                formatted_df = select(formatted_df, 
                    :wind_speed_range, :mean_ti, :std_ti, :representative_ti, :occurrence)
            end
            
            ti_ws_cols = [
                :wind_speed_range => "风速区间 (m/s)",
                :mean_ti => "平均湍流强度",
                :std_ti => "湍流强度标准差", 
                :representative_ti => "代表湍流强度(P90)"
            ]
            
            # Add IEC category column name if it exists
            if "iec_category" in names(formatted_df)
                push!(ti_ws_cols, :iec_category => "IEC类别")
            end
            
            push!(ti_ws_cols, :occurrence => "数据点数")
            
            rename!(formatted_df, ti_ws_cols...)
            
        elseif table_type == "summary"
            # Translate wind speed ranges to Chinese
            wind_speed_ranges_chinese = Dict(
                "all" => "全风速",
                ">3 m/s" => ">3 m/s",
                "14.5-16.5 m/s" => "14.5-16.5 m/s",
                "9.5-10.5 m/s" => "9.5-10.5 m/s"
            )
            
            formatted_df[!, :wind_speed_range] = map(formatted_df[!, :wind_speed_range]) do range
                get(wind_speed_ranges_chinese, range, range)
            end
            
            # Format numeric columns
            for col in names(formatted_df)
                if col in ["mast", "height", "wind_speed_range"]
                    continue
                elseif col in ["mean_ti", "representative_ti", "ti_std"]
                    formatted_values = [ismissing(v) ? "-" : string(round(v, digits=3)) 
                                      for v in formatted_df[!, col]]
                    formatted_df[!, col] = formatted_values
                end
            end
            
            # Select columns for summary table (exclude mast since it's in the title)
            formatted_df = select(formatted_df, :height, :wind_speed_range, :mean_ti, :representative_ti, :ti_std)
            
            summary_cols = [
                :height => "高度 (m)",
                :wind_speed_range => "风速范围",
                :mean_ti => "平均湍流强度",
                :representative_ti => "代表湍流强度(P90)", 
                :ti_std => "湍流强度标准差"
            ]
            rename!(formatted_df, summary_cols...)
        end
        
        return simple_table(formatted_df, round_digits=3)
    end
    
    # Write consolidated Typst report
    open(typst_path, "w") do io
        println(io, "== 测风塔$(mast_name)湍流强度分析报告")
        println(io)
        println(io, "== 基本信息")
        println(io, "- 测风塔：$(mast_name)")
        heights_str = join(sort(heights, rev=true), "m, ") * "m"
        println(io, "- 分析高度：$(heights_str)")
        println(io)
        
        # Generate sections for each height
        for height in sort(heights, rev=true)
            println(io, "== 测风塔$(mast_name) $(height)m高度湍流强度分析")
            println(io)
            
            # Load CSV files for this height
            sector_stats_path = joinpath(output_dir, "turbulence_intensity_$(height)m.csv")
            ti_by_ws_path = joinpath(output_dir, "ti_by_wind_speed_$(height)m.csv")
            report_path = joinpath(output_dir, "turbulence_intensity_report_$(height)m.csv")
            
            # Check if files exist
            files_exist = isfile(sector_stats_path) && isfile(ti_by_ws_path) && isfile(report_path)
            
            if !files_exist
                println(io, "数据文件缺失，跳过$(height)m高度分析")
                println(io)
                continue
            end
            
            # Load data
            sector_stats_df = CSV.read(sector_stats_path, DataFrame)
            ti_by_ws_df = CSV.read(ti_by_ws_path, DataFrame)
            report_df = CSV.read(report_path, DataFrame)
            
            # Sector statistics
            println(io, "=== 各风向扇区湍流强度统计")
            println(io, "表格：测风塔$(mast_name) $(height)m高度各风向扇区的湍流强度统计结果")
            println(io)
            sector_table = prepare_and_format_table(sector_stats_df, "sector")
            show(io, MIME"text/typst"(), sector_table)
            println(io)
            println(io)
            
            # TI by wind speed
            println(io, "=== 各风速区间湍流强度统计")
            println(io, "表格：测风塔$(mast_name) $(height)m高度不同风速区间的湍流强度统计结果")
            println(io)
            ti_ws_table = prepare_and_format_table(ti_by_ws_df, "wind_speed")
            show(io, MIME"text/typst"(), ti_ws_table)
            println(io)
            println(io)
        end
        
        # Consolidated summary for all heights
        if length(heights) > 1
            println(io, "== 测风塔$(mast_name)全高度湍流强度汇总")
            println(io)
            
            # Combine all report data
            all_report_data = DataFrame()
            for height in sort(heights)
                report_path = joinpath(output_dir, "turbulence_intensity_report_$(height)m.csv")
                if isfile(report_path)
                    report_df = CSV.read(report_path, DataFrame)
                    append!(all_report_data, report_df)
                end
            end
            
            if nrow(all_report_data) > 0
                println(io, "表格：测风塔$(mast_name)全高度不同风速范围的湍流强度汇总统计")
                println(io)
                summary_table = prepare_and_format_table(all_report_data, "summary")
                show(io, MIME"text/typst"(), summary_table)
                println(io)
                println(io)
            end
        end

        println(io, "== 测风塔$(mast_name)湍流强度与IEC标准对比")
        println(io)
        
        # Check if combined plot exists
        combined_plot_path = joinpath(output_dir, "iec_comparison_combined.png")
        if isfile(combined_plot_path)
            println(io, "#figure(")
            println(io, "  image(\"iec_comparison_combined.png\", width: 100%),")
            println(io, "  caption: [测风塔$(mast_name)湍流强度与IEC 61400-1标准对比 (高度 ≥ $(min_plot_height)m)]")
            println(io, ")")
            println(io)
        end
        
        println(io, "== IEC标准说明")
        println(io, "- IEC Category A: 高湍流强度 (I_ref = 0.16)")
        println(io, "- IEC Category B: 中等湍流强度 (I_ref = 0.14)")
        println(io, "- IEC Category C: 低湍流强度 (I_ref = 0.12)")
        println(io, "- IEC湍流强度计算公式：TI = I_ref × (0.75 + 5.6/V)")
        println(io)
        
        println(io, "== 分析说明")
        println(io, "- 湍流强度计算公式：TI = 风速标准差 / max(平均风速, 1.0)")
        println(io, "- 代表湍流强度（P90）：平均湍流强度 + 1.28 × 湍流强度标准差")
        println(io, "- 分析采用16个风向扇区，每个扇区22.5度")
        println(io, "- 风速区间统计采用1m/s间隔，从0-28m/s")
        println(io, "- 各风速范围统计用于不同工程应用需求")
        println(io, "- IEC类别判定基于代表湍流强度与IEC标准曲线的比较")
    end
    
    @info "Generated consolidated turbulence intensity Typst report: $typst_path"
    return nothing
end

export analyze_turbulence_intensity, analyze_all_turbulence, generate_turbulence_typst_reports

end # module 
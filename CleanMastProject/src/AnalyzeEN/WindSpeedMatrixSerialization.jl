module WindSpeedMatrixSerialization

using DataFrames
using Printf
using ...Types.AnalyzeENConfiguration: ENMastWindSpeedResult
using ..WindSpeed: create_direction_sectors

export serialize_header, serialize_vmean_by_direction, serialize_frequency_matrix, serialize_wind_speed_matrices

"""
    serialize_header(result::ENMastWindSpeedResult) -> String

Generate the header section with Label, X, Y, H, and GeoHash.
"""
function serialize_header(result::ENMastWindSpeedResult)::String
    lines = String[]
    push!(lines, @sprintf("Label = %s", result.Label))
    push!(lines, @sprintf("X     =             %d\t", floor(Int,result.X)))
    push!(lines, @sprintf("Y     =              %d\t", floor(Int,result.Y)))
    push!(lines, @sprintf("H     =           %d", result.H))
    push!(lines, @sprintf("GeoHash  = %s\t", result.GeoHash))
    return join(lines, "\n")
end

"""
    serialize_vmean_by_direction(result::ENMastWindSpeedResult) -> String

Generate the Vmean section with wind speed and frequency by direction.
"""
function serialize_vmean_by_direction(result::ENMastWindSpeedResult)::String
    lines = String[]
    
    # Vmean line
    push!(lines, @sprintf("Vmean =           %.5f", result.Vmean))
    
    # Direction header
    dir_line = " D              "
    for dir in result.VmeanByDirection.Direction
        dir_line *= @sprintf("%15.6f", dir)
    end
    push!(lines, dir_line)
    
    # Wind speed values
    v_line = " V              "
    for vmean in result.VmeanByDirection.Vmean
        v_line *= @sprintf("%15.1f", vmean)
    end
    push!(lines, v_line)
    
    # Frequency percentages
    freq_line = " %              "
    for freq in result.VmeanByDirection.Frequency
        freq_line *= @sprintf("%15.2f", freq * 100)  # Convert to percentage
    end
    push!(lines, freq_line)
    
    return join(lines, "\n")
end

"""
    serialize_frequency_matrix(result::ENMastWindSpeedResult) -> String

Generate the frequency by direction and speed matrix.
Note: The output values are scaled by 1000 (千分数) rather than raw frequencies.
"""
function serialize_frequency_matrix(result::ENMastWindSpeedResult)::String
    lines = String[]
    
    # Find the "All Sectors" row
    
    # Header line with directions (excluding "All Sectors")
    # Note: The sample shows a blank space after V, suggesting all_sectors header might be implicit
    header_line = "    V           "
    for dir in create_direction_sectors()
        header_line *= @sprintf("%15.6f", dir)
    end
    push!(lines, header_line)
    
    # Speed rows
    for row in eachrow(result.FrequencyByDirectionAndSpeed)
        speed_bin = row.SpeedBin
        
        # Format row: speed bin followed by direction values, then all sectors at the end
        row_line = @sprintf("%5d", speed_bin)

        row_line *= map(collect(row[2:end])) do value
            @sprintf("%15.4g", value * 1000)  # Scale factor is 1000 (千分数)
        end |> join
        push!(lines, row_line)
    end
    
    return join(lines, "\n")
end

"""
    serialize_single_matrix(result::ENMastWindSpeedResult) -> String

Serialize a single wind speed matrix to the required text format.
"""
function serialize_single_matrix(result::ENMastWindSpeedResult)::String
    sections = String[]
    
    # Header section
    push!(sections, serialize_header(result))
    push!(sections, "")  # Blank line
    
    # Vmean section
    push!(sections, serialize_vmean_by_direction(result))
    push!(sections, "")  # Blank line
    
    # Frequency matrix section
    push!(sections, serialize_frequency_matrix(result))
    push!(sections, "")  # Blank line
    
    # Footer line
    push!(sections, "-" ^ 217)
    
    return join(sections, "\n")
end

"""
    serialize_wind_speed_matrices(results::Vector{ENMastWindSpeedResult}) -> Dict{String, String}

Serialize multiple wind speed matrices to the required text format.
Returns a dictionary mapping mast labels to their serialized content.
"""
function serialize_wind_speed_matrices(results::Vector{ENMastWindSpeedResult})::Dict{String, String}
    matrices = Dict{String, String}()
    
    for result in results
        matrices[result.Label] = serialize_single_matrix(result)
    end
    
    return matrices
end

end # module 
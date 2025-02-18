module Sector

import ..Utils: from_dict, to_dict

export DIRECTION_16_SECTORS, get_direction_sector, DirectionSector

"""
Represents a wind direction sector with a name and center angle
"""
struct DirectionSector
    name::String
    center::Float64
    width::Float64
end

"""
    to_dict(sector::DirectionSector) :: Dict{String, Any}

Convert a DirectionSector to a dictionary representation.
"""
function to_dict(sector::DirectionSector) :: Dict{String, Any}
    return Dict{String, Any}(
        "name" => sector.name,
        "center" => sector.center,
        "width" => sector.width
    )
end

"""
    from_dict(::Type{DirectionSector}, dict::Dict{String, Any}) :: DirectionSector

Create a DirectionSector from a dictionary representation.
"""
function from_dict(::Type{DirectionSector}, dict::Dict{String, Any}) :: DirectionSector
    return DirectionSector(
        dict["name"],
        dict["center"],
        dict["width"]
    )
end

# Constants for direction sectors
const DIRECTION_16_SECTORS = [
    DirectionSector("N", 0.0, 22.5),
    DirectionSector("NNE", 22.5, 22.5),
    DirectionSector("NE", 45.0, 22.5),
    DirectionSector("ENE", 67.5, 22.5),
    DirectionSector("E", 90.0, 22.5),
    DirectionSector("ESE", 112.5, 22.5),
    DirectionSector("SE", 135.0, 22.5),
    DirectionSector("SSE", 157.5, 22.5),
    DirectionSector("S", 180.0, 22.5),
    DirectionSector("SSW", 202.5, 22.5),
    DirectionSector("SW", 225.0, 22.5),
    DirectionSector("WSW", 247.5, 22.5),
    DirectionSector("W", 270.0, 22.5),
    DirectionSector("WNW", 292.5, 22.5),
    DirectionSector("NW", 315.0, 22.5),
    DirectionSector("NNW", 337.5, 22.5)
]

# Helper functions for sector bounds
function sector_start(sector::DirectionSector)::Float64
    mod(sector.center - sector.width/2, 360)
end

function sector_end(sector::DirectionSector)::Float64
    mod(sector.center + sector.width/2, 360)
end

"""
Calculate the smallest angle difference between two angles in degrees
"""
function abs_degree_diff(a1::Float64, a2::Float64)::Float64
    return abs(degree_diff(a1, a2))
end
export abs_degree_diff

"""
Calculate the angle difference between two angles in degrees.
Returns the smallest angle difference in the range [-180, 180) degrees.
"""
function degree_diff(a1::Float64, a2::Float64)::Float64
    return mod(a1 - a2 + 180.0, 360.0) - 180.0
end
export degree_diff

"""
Get the direction sector for a given wind direction in degrees
"""
function get_direction_sector(direction::Float64, sectors::Vector{DirectionSector})::Union{DirectionSector, Nothing}
    # Normalize direction to [0, 360)
    normalized_dir = mod(direction, 360.0)
    # Find the closest sector using proper angle difference
    sector_idx = argmin(map(sector -> abs_degree_diff(normalized_dir, sector.center), sectors))
    sector = sectors[sector_idx]
    if (abs_degree_diff(normalized_dir, sector.center) <= (0.001+sector.width/2))
        return sector
    else
        return nothing
    end
end

end # module 
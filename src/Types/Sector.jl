module Sector

export DIRECTION_SECTORS, SECTOR_DEGREES, get_direction_sector, DirectionSector

"""
Represents a wind direction sector with a name and center angle
"""
struct DirectionSector
    name::String
    center::Float64
end

# Constants for direction sectors
const DIRECTION_SECTORS = [
    DirectionSector("N", 0.0),
    DirectionSector("NNE", 22.5),
    DirectionSector("NE", 45.0),
    DirectionSector("ENE", 67.5),
    DirectionSector("E", 90.0),
    DirectionSector("ESE", 112.5),
    DirectionSector("SE", 135.0),
    DirectionSector("SSE", 157.5),
    DirectionSector("S", 180.0),
    DirectionSector("SSW", 202.5),
    DirectionSector("SW", 225.0),
    DirectionSector("WSW", 247.5),
    DirectionSector("W", 270.0),
    DirectionSector("WNW", 292.5),
    DirectionSector("NW", 315.0),
    DirectionSector("NNW", 337.5)
]

# Extract sector degrees for easier comparison
const SECTOR_DEGREES = [sector.center for sector in DIRECTION_SECTORS]

"""
Calculate the smallest angle difference between two angles in degrees
"""
function abs_degree_diff(a1::Float64, a2::Float64)::Float64
    diff = abs(mod(a1, 360.0) - mod(a2, 360.0))
    return min(diff, 360.0 - diff)
end
export abs_degree_diff

"""
Get the direction sector for a given wind direction in degrees
"""
function get_direction_sector(direction::Float64)::DirectionSector
    # Normalize direction to [0, 360)
    normalized_dir = mod(direction, 360.0)
    # Find the closest sector using proper angle difference
    sector_idx = argmin([abs_degree_diff(deg, normalized_dir) for deg in SECTOR_DEGREES])
    return DIRECTION_SECTORS[sector_idx]
end

end # module 
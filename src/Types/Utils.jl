module Utils

"""
Generic from_dict function that can be overridden by specific types
"""
function from_dict(::Type{T}, dict::Dict{String, Any}) :: T where T
    error("from_dict not implemented for type $T")
end

"""
Generic to_dict function that can be overridden by specific types
"""
function to_dict(obj::T) :: Dict{String, Any} where T
    error("to_dict not implemented for type $T")
end

"""
Show an object as a DataFrame, to export to other programs for future analysis
"""
function show_as_dataframe(obj::T) :: DataFrame where T
    error("show_as_dataframe not implemented for type $T")
end

"""
Read an object from a file on disk, a list of file is provided, so if one fails, the others will be tried
"""
function from_disk(paths :: Vector{String})
    error("from_disk not implemented for type $T")
end

"""
Write an object to files on disk. A vector of file paths is provided, so different formats can be written simultaneously.
"""
function to_disk(paths:: Vector{String}, obj::T) where T
    error("to_disk not implemented for type $T")
end

"""
    strip_nothing_values(d::Dict)

Recursively remove key-value pairs from a dictionary where the value is `nothing`.
This is useful for preparing data to be saved in formats like TOML that do not support null types.
"""
function strip_nothing_values(d::Dict{String, Any}) :: Dict{String, Any}
    clean_dict = Dict{String, Any}()
    for (k, v) in d
        if v isa Dict
            clean_dict[k] = strip_nothing_values(v)
        elseif v isa Vector
            # Process each item in the vector, stripping nothing from nested dicts
            clean_dict[k] = [item isa Dict ? strip_nothing_values(Dict{String, Any}(item)) : item for item in v]
        elseif !isnothing(v)
            clean_dict[k] = v
        end
    end
    return clean_dict
end

export from_dict, to_dict, show_as_dataframe, from_disk, to_disk, strip_nothing_values

end 
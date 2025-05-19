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

export from_dict, to_dict, show_as_dataframe, from_disk, to_disk

end 
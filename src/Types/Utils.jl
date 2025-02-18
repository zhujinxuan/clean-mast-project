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

export from_dict, to_dict, show_as_dataframe

end 
module Utils

export format_height

"""
    format_height(height::Float64)::String

Format height for display, showing as integer if it's a whole number, otherwise with one decimal place.

# Examples
```julia
format_height(120.0)   # "120"
format_height(78.5)    # "78.5"
format_height(89.0)    # "89"
format_height(38.75)   # "38.8" (rounded to 1 decimal)
```
"""
function format_height(height::Float64)::String
    if height == round(height)
        return "$(Int(round(height)))"
    else
        return "$(round(height, digits=1))"
    end
end

end # module

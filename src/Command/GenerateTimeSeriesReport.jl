module GenerateTimeSeriesReport

using ...Types.CleanMastConfig: ProjectConfig
using ...CleanMastConfig: parse_config
using Dates

"""
Generate a Typst file that includes all SVGs and CSVs from timeseries analysis
"""
function generate_typst_report(project_dir::String)
    # Create analysis directory if it doesn't exist
    analysis_dir = joinpath(project_dir, "analysis")
    mkpath(analysis_dir)
    
    # Define the timeseries types that we expect to have analysis for
    # Reversed order to put representative year first
    timeseries_types = [
        "representative-year",
        "reconstruct-meso",
        "reconstruct-single",
        "tower-shading"
    ]
    
    # Define the analysis outputs we expect for each timeseries type
    analysis_outputs = [
        "wind_speed_timeseries",
        "daily_pattern",
        "vertical_profile",
        "monthly_pattern"
    ]
    
    # Create the Typst file
    typst_file = joinpath(analysis_dir, "timeseries.typ")
    
    open(typst_file, "w") do io
        # Write the document header
        write(io, """
        #import "@preview/tablex:0.0.6": tablex, cellx, rowspanx, colspanx
        
        #set page(
          margin: (x: 2cm, y: 2cm),
          numbering: "1",
          number-align: center,
        )
        
        #set heading(numbering: "1.")
        
        #align(center)[
          #text(size: 24pt)[*Wind Mast Time Series Analysis*]
          
          #v(0.5cm)
          
          #text(size: 14pt)[Generated on #datetime.today().display()]
        ]
        
        #pagebreak()
        
        #outline(
          title: [Table of Contents],
          indent: true,
        )
        
        #pagebreak()
        
        = Introduction
        
        This report contains the analysis of time series data from wind mast measurements.
        The analysis includes:
        
        - Wind speed time series visualization
        - Daily wind speed patterns (24-hour)
        - Vertical wind speed profiles
        - Monthly wind speed patterns
        - Weibull distribution analysis
        
        The analysis is performed on different data sources:
        
        """)
        
        # Add descriptions for each timeseries type
        descriptions = Dict(
            "tower-shading" => "Tower shading corrected data",
            "reconstruct-single" => "Single mast reconstruction data",
            "reconstruct-meso" => "Meso-scale reconstruction data",
            "representative-year" => "Representative year data"
        )
        
        for ts_type in timeseries_types
            write(io, "- *$(descriptions[ts_type])*: Data from the $(ts_type) processing step\n")
        end
        
        # Add sections for each timeseries type
        for ts_type in timeseries_types
            ts_dir = joinpath(project_dir, "analysis", ts_type)
            
            # Skip if directory doesn't exist
            if !isdir(ts_dir)
                continue
            end
            
            # Add section header
            write(io, """
            
            #pagebreak()
            
            = $(descriptions[ts_type])
            
            """)
            
            # Add subsections for each analysis output
            for output in analysis_outputs
                svg_file = joinpath(ts_type, "$(output).svg")
                csv_file = joinpath(ts_type, "$(output).csv")
                
                # Skip if files don't exist
                if !isfile(joinpath(project_dir, "analysis", svg_file))
                    continue
                end
                
                # Format the output name for display
                display_name = replace(output, "_" => " ")
                display_name = titlecase(display_name)
                
                write(io, """
                
                == $(display_name)
                
                #figure(
                  image("$(svg_file)", width: 80%),
                  caption: [$(display_name) for $(descriptions[ts_type])],
                )
                
                """)
                
                # Import CSV data directly into the document for specific outputs
                if output in ["daily_pattern", "monthly_pattern", "vertical_profile"]
                    write(io, """
                    === Data Table
                    
                    The following table shows the raw data used for the $(lowercase(display_name)) analysis:
                    
                    """)
                    
                    # Use a more direct approach to create tables from CSV data
                    write(io, """
                    #let data = csv("$(csv_file)")
                    
                    // Set up table formatting
                    #set table(inset: 10pt)
                    
                    #figure(
                      table(
                        columns: data.at(0).len(),
                        align: center,
                        // Header row with bold formatting
                        ..data.at(0).map(cell => [*#cell*]),
                        
                        // Data rows with number formatting to 2 decimal places
                        ..data.slice(1).flatten().map(cell => {
                          if type(cell) == "string" and cell.match(regex("^-?[0-9]+\\\\.[0-9]+\$")) != none {
                            // Convert to number and format to 2 decimal places using floor(x*100)/100
                            let num = float(cell)
                            let formatted = calc.floor(num * 100) / 100
                            [#formatted]
                          } else {
                            [#cell]
                          }
                        })
                      ),
                      caption: [$(display_name) data for $(descriptions[ts_type])]
                    )
                    
                    """)
                else
                    # For wind_speed_timeseries, just add a link to the CSV file
                    write(io, """
                    The raw data for this analysis is available in the CSV file: `$(csv_file)`
                    
                    """)
                end
            end
            
            # Add Weibull analysis section if it exists
            weibull_dir = joinpath(ts_dir, "weibull")
            if isdir(weibull_dir)
                write(io, """
                
                == Weibull Distribution Analysis
                
                The Weibull distribution is commonly used to characterize wind speed distributions.
                The following analysis shows the fitted Weibull distributions at different heights.
                
                === Weibull Parameters
                
                The table below shows the Weibull shape (k) and scale (c) parameters at each height:
                
                """)
                
                # Add Weibull parameters table
                params_file = joinpath(ts_type, "weibull", "weibull_parameters.csv")
                if isfile(joinpath(project_dir, "analysis", params_file))
                    write(io, """
                    #let data = csv("$(params_file)")
                    
                    // Set up table formatting
                    #set table(inset: 10pt)
                    
                    #figure(
                      table(
                        columns: data.at(0).len(),
                        align: center,
                        // Header row with bold formatting
                        ..data.at(0).map(cell => [*#cell*]),
                        
                        // Data rows with number formatting to 2 decimal places
                        ..data.slice(1).flatten().map(cell => {
                          if type(cell) == "string" and cell.match(regex("^-?[0-9]+\\\\.[0-9]+\$")) != none {
                            // Convert to number and format to 2 decimal places using floor(x*100)/100
                            let num = float(cell)
                            let formatted = calc.floor(num * 100) / 100
                            [#formatted]
                          } else {
                            [#cell]
                          }
                        })
                      ),
                      caption: [Weibull distribution parameters for $(descriptions[ts_type])]
                    )
                    
                    """)
                end
                
                # Add Weibull distribution plots
                write(io, """
                
                === Weibull Distribution Plots
                
                The following plots show the wind speed frequency distributions and fitted Weibull curves at each height:
                
                """)
                
                # Find all Weibull SVG files
                weibull_svgs = filter(f -> endswith(f, ".svg"), readdir(weibull_dir))
                
                # Sort by height (extract height from filename)
                sort!(weibull_svgs, by = f -> begin
                    m = match(r"weibull_(\d+)m\.svg", f)
                    m === nothing ? 0 : parse(Int, m[1])
                end)
                
                # Add each SVG to the document
                for svg_file in weibull_svgs
                    # Skip the parameters file
                    if svg_file == "weibull_parameters.svg"
                        continue
                    end
                    
                    # Extract height from filename
                    height_match = match(r"weibull_(\d+)m\.svg", svg_file)
                    if height_match !== nothing
                        height = height_match[1]
                        
                        # Add the figure
                        rel_path = joinpath(ts_type, "weibull", svg_file)
                        write(io, """
                        #figure(
                          image("$(rel_path)", width: 80%),
                          caption: [Weibull distribution at $(height)m for $(descriptions[ts_type])],
                        )
                        
                        """)
                    end
                end
            end
        end
    end
    
    return typst_file
end

"""
Main entry point for generate timeseries report command
"""
function execute(project_dir::String)
    # Generate the Typst report
    typst_file = generate_typst_report(project_dir)
    
    # Compile the Typst file
    output_pdf = replace(typst_file, ".typ" => ".pdf")
    run(`typst compile $(typst_file) $(output_pdf)`)
    
    @info "Generated timeseries report: $(output_pdf)"
    
    return 0
end

end # module 
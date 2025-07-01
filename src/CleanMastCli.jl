module CleanMastCli

using Comonicon

"""
project

Project setup and management commands
"""
Comonicon.@cast module Project
    using Comonicon
    using CleanMastProject.Command.QuickStart
    using CleanMastProject.ParseSensors.CommandParseSensors

    """
    init

    Create a new project with example config.

    # Arguments
    - `dir`: Project directory
    """
    Comonicon.@cast function init(dir::String)
        QuickStart.execute(dir)
    end

    """
    parse-sensors

    Process sensor data based on a TOML configuration file.
    Creates raw data files and sensor metadata files.

    # Arguments
    - `config_path`: Path to the parse-sensors.toml configuration file.

    # Example
    ```bash
    julia bin/CleanMast.jl project parse-sensors path/to/project/parse-sensors.toml
    ```
    """
    Comonicon.@cast function parse_sensors(config_path::String)
        CommandParseSensors.execute(config_path)
    end
end

"""
process

Data processing and reconstruction commands
"""
Comonicon.@cast module Process
    using Comonicon
    using CleanMastProject.DataClean.ProcessCleanCommand
    using CleanMastProject.TowerShading.CommandTowerShading
    using CleanMastProject.ReconstructSingleMast.CommandReconstructSingle
    using CleanMastProject.TrainMeso.CommandTrainMeso
    using CleanMastProject.ReconstructMeso.CommandReconstructMeso
    using CleanMastProject.RepresentativeYear.CommandRepresentativeYear
    using CleanMastProject.WTTimeSeries.CommandWtTimeSeries
    using CleanMastProject.Command.ProcessAll

    """
    clean

    Clean data using configured rules.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function clean(config_path::String)
        ProcessCleanCommand.execute(config_path)
    end

    """
    tower-shading

    Apply tower shading detection and correction.

    # Arguments
    - `dir`: Project directory containing config.yaml
          """
      Comonicon.@cast function tower_shading(config_path::String)
                     CommandTowerShading.execute(config_path)
      end

    """
    reconstruct-single

    Reconstruct missing data using single mast data.

    # Arguments
    - `config_path`: Path to reconstruct-single.toml configuration file
    """
    Comonicon.@cast function reconstruct_single(config_path::String)
        CommandReconstructSingle.execute(config_path)
    end

    """
    train-meso

    Train mast and meso linear correlation models.

    # Arguments
    - `config_path`: Path to train-meso.toml configuration file
    """
    Comonicon.@cast function train_meso(config_path::String)
        CommandTrainMeso.execute(config_path)
    end

    """
    reconstruct-meso

    Reconstruct missing data using trained mesoscale models.

    # Arguments
    - `config_path`: Path to reconstruct-meso.toml configuration file
    """
    Comonicon.@cast function reconstruct_meso(config_path::String)
        CommandReconstructMeso.execute(config_path)
    end

    """
    representative-year

    Calibrate data to a representative year.

    # Arguments
    - `config_path`: Path to representative-year.toml configuration file
    """
    Comonicon.@cast function representative_year(config_path::String)
        CommandRepresentativeYear.execute(config_path)
    end

    """
    wt-timeseries

    Process wind turbine time series data.
    Extracts wind speed and direction data at target heights from representative year data.
    Saves timestamp, wind speed, and wind direction to CSV files.

    # Arguments
    - `config_path`: Path to wt-timeseries.toml configuration file
    """
    Comonicon.@cast function wt_timeseries(config_path::String)
        CommandWtTimeSeries.execute(config_path)
    end

    """
    all

    Execute all processing steps in sequence:
    1. Clean data
    2. Tower shading
    3. Reconstruct single mast
    4. Train meso models
    5. Reconstruct meso
    6. Representative year calibration

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function all(dir::String)
        ProcessAll.execute(dir)
    end
end

@cast module Recommend
    using Comonicon
    using CleanMastProject.DataClean.RecommendProcessCleanCommand
    using CleanMastProject.TowerShading.RecommendTowerShadingCommand
    using CleanMastProject.ReconstructSingleMast.RecommendReconstructSingleCommand
    using CleanMastProject.TrainMeso.RecommendTrainMesoCommand
    using CleanMastProject.ReconstructMeso.RecommendReconstructMesoCommand
    using CleanMastProject.RepresentativeYear.RecommendRepresentativeYearCommand
    using CleanMastProject.WTTimeSeries.RecommendWtTimeSeriesCommand

    """
    recommend process-clean <dir>

    Recommend a process-clean.toml file for the project

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    @cast function process_clean(dir::String)
        "Recommend a process-clean.toml file for the project"
        RecommendProcessCleanCommand.execute(dir)
    end
    
    @cast function tower_shading(dir::String)
        "Recommend a tower-shading.toml file for the project"
        RecommendTowerShadingCommand.execute(dir)
    end
    
    @cast function reconstruct_single(dir::String)
        "Recommend a reconstruct-single.toml file for the project"
        RecommendReconstructSingleCommand.execute(dir)
    end
    
    @cast function train_meso(dir::String)
        "Recommend a train-meso.toml file for the project"
        RecommendTrainMesoCommand.execute(dir)
    end
    
    @cast function reconstruct_meso(dir::String)
        "Recommend a reconstruct-meso.toml file for the project"
        RecommendReconstructMesoCommand.execute(dir)
    end
    
    @cast function representative_year(dir::String)
        "Recommend a representative-year.toml file for the project"
        RecommendRepresentativeYearCommand.execute(dir)
    end
    
    @cast function wt_timeseries(dir::String)
        "Recommend a wt-timeseries.toml file for the project"
        RecommendWtTimeSeriesCommand.execute(dir)
    end
end

"""
analyze

Analysis and reporting commands
"""
Comonicon.@cast module Analyze
    using Comonicon
    using CleanMastProject.Command.AnalyzeTimeSeriesCommand
    using CleanMastProject.Command.AnalyzeEN
    using CleanMastProject.Command.AnalyzeReconstructSingle

    """
    timeseries

    Analyze time series data using an analyze configuration file.

    # Arguments
    - `config_path`: Path to analyze.yaml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl analyze timeseries path/to/analyze.yaml
    ```

    The analyze.yaml file should specify:
    - Multiple masts with their data files and sensor configurations
    - Air density settings for each mast
    - Output directory for results
    - Optional DOCX report settings

    For each mast, generates:
    - Wind temporal analysis (time series, daily/monthly patterns)
    - Vertical profile analysis
    - Wind direction frequency and power distribution
    - Wind rose plots (frequency and power)
    - Turbulence intensity analysis (with meteodyn_ti.txt)
    - Weibull distribution analysis
    """
    Comonicon.@cast function timeseries(config_path::String)
        AnalyzeTimeSeriesCommand.execute(config_path)
    end

    """
    en

    Analyze wind data for EN standard (civil engineering load calculations).

    # Arguments
    - `config_path`: Path to analyze-en.yaml configuration file

    # Options
    - `--output, -o`: Output directory for results

    # Example
    ```bash
    julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml
    julia bin/CleanMast.jl analyze en path/to/analyze-en.yaml --output results/
    ```

    The analyze-en.yaml file should specify:
    - Multiple masts with their coordinates and measurement height
    - Input data and sensor configuration paths
    - Optional GeoHash for location encoding

    Generates a single WindSpeedMatrix.txt file containing all masts with:
    - Mean wind speed (Vmean)
    - Mean wind speed by direction sectors (15-degree bins)
    - Frequency distribution by direction and wind speed
    """
    Comonicon.@cast function en(config_path::String; output::Union{String, Nothing}=nothing)
        AnalyzeEN.execute(config_path, output)
    end

    """
    reconstruct-single

    Compare time series data before and after single mast reconstruction.

    # Arguments
    - `config_path`: Path to analyze-reconstruct-single.yaml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl analyze reconstruct-single path/to/analyze-reconstruct-single.yaml
    ```

    The YAML configuration file should specify:
    - Multiple masts with before/after reconstruction data files and sensor configurations
    - Output directory for results (default: ./analyze-reconstruct-single)

    For each mast, generates:
    - Missing data points count before/after reconstruction
    - Reconstruction rate and data coverage ratio
    - R² matrix of wind speed correlations between heights
    - Mean and standard deviation of wind direction differences between heights
    - Comprehensive Typst report in Chinese
    """
    Comonicon.@cast function reconstruct_single(config_path::String)
        AnalyzeReconstructSingle.execute(config_path)
    end
end

"""
CleanMast - Wind measurement data cleaning and analysis tool

A command-line tool for processing wind measurement data.
"""
Comonicon.@main

end # module CleanMastCli
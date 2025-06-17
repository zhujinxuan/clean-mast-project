module CleanMastCli

using Comonicon

"""
project

Project setup and management commands
"""
Comonicon.@cast module Project
    using Comonicon
    using CleanMastProject.Command.QuickStart
    using CleanMastProject.Command.CheckConfig
    using CleanMastProject.Command.CleanFiles
    using CleanMastProject.Command.ParseSensors

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
    check-config

    Validate configuration files.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function check_config(dir::String)
        CheckConfig.execute(dir)
    end

    """
    clean-files

    Archive non-essential files.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function clean_files(dir::String)
        CleanFiles.execute(dir)
    end

    """
    parse-sensors

    Process sensors for both mast and meso data.
    Creates raw data files and sensor metadata files.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function parse_sensors(dir::String)
        ParseSensors.execute(dir)
    end
end

"""
process

Data processing and reconstruction commands
"""
Comonicon.@cast module Process
    using Comonicon
    using CleanMastProject.Command.CleanData
    using CleanMastProject.Command.TowerShading
    using CleanMastProject.Command.ReconstructSingleMast
    using CleanMastProject.Command.TrainMesoModel
    using CleanMastProject.Command.ReconstructMeso
    using CleanMastProject.Command.RepresentativeYearCalibration
    using CleanMastProject.Command.WtTimeSeries
    using CleanMastProject.Command.ProcessAll

    """
    clean

    Clean data using configured rules.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function clean(dir::String)
        CleanData.execute(dir)
    end

    """
    tower-shading

    Apply tower shading detection and correction.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function tower_shading(dir::String)
        TowerShading.execute(dir)
    end

    """
    reconstruct-single

    Reconstruct missing data using single mast data.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function reconstruct_single(dir::String)
        ReconstructSingleMast.execute(dir)
    end

    """
    train-meso

    Train mast and meso linear correlation models.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function train_meso(dir::String)
        TrainMesoModel.execute(dir)
    end

    """
    reconstruct-meso

    Reconstruct missing data using trained mesoscale models.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function reconstruct_meso(dir::String)
        ReconstructMeso.execute(dir)
    end

    """
    representative-year

    Calibrate data to a representative year.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function representative_year(dir::String)
        RepresentativeYearCalibration.execute(dir)
    end

    """
    wt-timeseries

    Process wind turbine time series data.
    Extracts wind speed and direction data at target height from representative year data.
    Saves timestamp, wind speed, and wind direction to a CSV file.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function wt_timeseries(dir::String)
        WtTimeSeries.execute(dir)
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
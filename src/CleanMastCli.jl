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
    using CleanMastProject.ReconstructCross.ProcessReconstructCrossCommand

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
    reconstruct-cross

    Execute cross-mast reconstruction using trained models.

    # Arguments
    - `config_path`: Path to reconstruct-cross.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl process reconstruct-cross reconstruct-cross.toml
    ```

    The TOML configuration file should specify:
    - Masts with input data sources and output paths
    - Reconstruction jobs with trained model paths
    - Priority levels for reconstruction order
    - Settings for reconstruction execution

    For each reconstruction job:
    - Loads trained cross-mast models from JLD2 files
    - Applies reconstruction to fill missing data points only
    - Preserves existing measurements (configurable)
    - Generates quality metrics and validation reports
    - Saves reconstructed time series files

    Reconstruction is executed in priority order:
    - Priority 1: Excellent correlations (≥0.9)
    - Priority 2: Good correlations (≥0.8)
    - Priority 3: Acceptable correlations (≥0.7)
    """
    Comonicon.@cast function reconstruct_cross(config_path::String)
        ProcessReconstructCrossCommand.execute(config_path)
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
train

Model training commands
"""
Comonicon.@cast module Train
    using Comonicon
    using CleanMastProject.TrainReconstructCross.TrainReconstructCrossCommand

    """
    reconstruct-cross

    Train cross-mast relationships and reconstruction models.

    # Arguments
    - `config_path`: Path to train-reconstruct-cross.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl train reconstruct-cross path/to/train-reconstruct-cross.toml
    ```

    The TOML configuration file should specify:
    - Multiple masts with reconstructed time series data files and sensor configurations
    - Training settings including model parameters
    - Output directory for results (default: ./train-reconstruct-cross)

    For each mast pair, trains:
    - Data coverage and overlap duration analysis
    - Wind speed correlations between high-elevation sensors (≥120m)
    - Wind direction differences and standard deviations
    - Cross-mast reconstruction models saved as .jld2 files
    - Machine-readable results for the recommend command

    Selection criteria for qualified pairs:
    - Speed reconstruction: ≥120 days overlap, ≥0.7 correlation (high-elevation sensors)
    - Direction reconstruction: ≥120 days overlap, ≤12.5° std deviation (high-elevation sensors)
    """
    Comonicon.@cast function reconstruct_cross(config_path::String)
        TrainReconstructCrossCommand.execute(config_path)
    end
end

@cast module Recommend
    using Comonicon
    using CleanMastProject.DataClean.RecommendProcessCleanCommand
    using CleanMastProject.TowerShading.RecommendTowerShadingCommand
    using CleanMastProject.ReconstructSingleMast.RecommendReconstructSingleCommand
    using CleanMastProject.TrainMeso.RecommendTrainMesoCommand
    using CleanMastProject.ReconstructMeso.RecommendReconstructMesoCommand
    using CleanMastProject.TrainReconstructCross.RecommendTrainReconstructCrossCommand
    using CleanMastProject.AnalyzeReconstructCross.RecommendAnalyzeReconstructCrossCommand
    using CleanMastProject.ReconstructCross.RecommendReconstructCrossCommand
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
    
    @cast function train_reconstruct_cross(dir::String)
        "Recommend a train-reconstruct-cross.toml file for cross-mast training"
        RecommendTrainReconstructCrossCommand.execute(dir)
    end
    
    @cast function analyze_reconstruct_cross(dir::String)
        "Recommend an analyze-reconstruct-cross.toml file for cross-mast analysis"
        RecommendAnalyzeReconstructCrossCommand.execute(dir)
    end

    @cast function reconstruct_cross(train_results_path::String, output_dir::String = "./")
        "Recommend a reconstruct-cross.toml file from training results"
        RecommendReconstructCrossCommand.execute(train_results_path, output_dir)
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
    using CleanMastProject.AnalyzeReconstructCross.CommandAnalyzeReconstructCross

    """
    timeseries

    Analyze time series data using an analyze configuration file.

    # Arguments
    - `config_path`: Path to analyze configuration file (supports .yaml, .toml, .json)

    # Examples
    ```bash
    julia bin/CleanMast.jl analyze timeseries path/to/analyze.yaml
    julia bin/CleanMast.jl analyze timeseries path/to/analyze.toml
    julia bin/CleanMast.jl analyze timeseries path/to/analyze.json
    ```

    The configuration file should specify:
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

    """
    reconstruct-cross

    Analyze cross-mast relationships and generate comprehensive reports.

    # Arguments
    - `config_path`: Path to analyze-reconstruct-cross.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl analyze reconstruct-cross path/to/analyze-reconstruct-cross.toml
    ```

    The TOML configuration file should specify:
    - Multiple masts with reconstructed time series data files and sensor configurations
    - Analysis settings including output directory and report format
    - Language preference (default: Chinese)

    For each mast pair, generates:
    - Wind speed correlation analysis with scatter plots and regression parameters
    - Wind direction relationship analysis with offset and standard deviation
    - Data coverage statistics and overlap duration
    - Individual PNG plots for each mast pair
    - Individual CSV data exports for each pair
    - Comprehensive Chinese Typst report with embedded visualizations

    Output includes:
    - report.typ: Main Chinese report with all analysis results
    - plots/: Individual plot files ({target}_{source}_speed_correlations.png, etc.)
    - tables/: Individual table files for each mast pair
    - data/: CSV exports for further analysis
    """
    Comonicon.@cast function reconstruct_cross(config_path::String)
        CommandAnalyzeReconstructCross.execute(config_path)
    end

end

"""
CleanMast - Wind measurement data cleaning and analysis tool

A command-line tool for processing wind measurement data.
"""
Comonicon.@main

end # module CleanMastCli
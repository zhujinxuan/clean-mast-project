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
    using CleanMastProject.Command.ProcessSteps
    using CleanMastProject.ReconstructCross.ProcessReconstructCrossCommand
    using CleanMastProject.GuessMastFromMeso.CommandGuessMastFromMeso

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
    guess-mast-from-meso

    Generate synthetic mast data from mesoscale data using mean speed matching.

    # Arguments
    - `config_path`: Path to guess-mast-from-meso.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl process guess-mast-from-meso guess-mast-from-meso.toml
    ```

    Generates synthetic mast data by scaling meso wind speeds to match target mean values.
    """
    Comonicon.@cast function guess_mast_from_meso(config_path::String)
        CommandGuessMastFromMeso.guess_mast_from_meso_command(config_path)
    end

    """
    steps

    Execute processing steps with flexible control options.

    # Arguments
    - `dir`: Project directory containing configurations
    - `--all`: Execute all processing steps (1-18)
    - `--from`: Starting step number (1-18, default: 1 when --all is used)
    - `--to`: Ending step number (1-18, default: 18 when --all is used)
    - `--list`: List all available steps without executing

    # Examples
    ```bash
    julia bin/CleanMast.jl process steps --all ./projects/my-project
    julia bin/CleanMast.jl process steps --from 5 --to 12 ./projects/my-project
    julia bin/CleanMast.jl process steps --from 10 ./projects/my-project
    julia bin/CleanMast.jl process steps --list
    ```

    Execute processing pipeline in flexible steps for better control and debugging.
    """
    Comonicon.@cast function steps(dir::String=""; all::Bool=false, from::Int=0,
                                  to::Int=0, list::Bool=false)
        from_step = from == 0 ? nothing : from
        to_step = to == 0 ? nothing : to
        ProcessSteps.execute(dir, all=all, from_step=from_step, to_step=to_step, list_only=list)
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

"""
guess

Generate and process synthetic data
"""
@cast module Guess
    using Comonicon
    using CleanMastProject.GuessMastFromMeso.CommandGuessMastFromMeso

    """
    mast-from-meso

    Generate synthetic mast data from mesoscale data using mean speed matching.

    # Arguments
    - `config_path`: Path to guess-mast-from-meso.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl guess mast-from-meso guess-mast-from-meso.toml
    ```

    Generates synthetic mast data by scaling meso wind speeds to match target mean values.
    """
    @cast function mast_from_meso(config_path::String)
        CommandGuessMastFromMeso.guess_mast_from_meso_command(config_path)
    end
end

@cast module Bootstrap
    using Comonicon
    using CleanMastProject.GuessMastFromMeso.CommandGuessMastFromMeso

    """
    guess-mast-from-meso

    Bootstrap a guess-mast-from-meso.toml configuration file from meso data.

    # Arguments
    - `--meso`: Path to meso data CSV file (sensors file auto-detected as basename.sensors.toml)
    - `--output`: Output path for configuration file (default: ../{meso-basename}.guess-mast-from-meso.toml relative to meso directory)

    # Example
    ```bash
    julia bin/CleanMast.jl bootstrap guess-mast-from-meso --meso ./raw/era5.csv
    ```

    Generates an incomplete configuration file with TODO fields that need to be filled in manually.
    Output paths: ./guessed-masts/{meso-basename}-vm.csv and ./guessed-masts/{meso-basename}-vm.sensors.toml
    """
    @cast function guess_mast_from_meso(; meso::String, output::Union{String, Nothing}=nothing)
        CommandGuessMastFromMeso.bootstrap_guess_mast_from_meso_command(meso=meso, output=output)
    end
end

@cast module Recommend
    using Comonicon
    using CleanMastProject.ParseSensors.RecommendParseSensorsCommand
    using CleanMastProject.DataClean.RecommendProcessCleanCommand
    using CleanMastProject.TowerShading.RecommendTowerShadingCommand
    using CleanMastProject.ReconstructSingleMast.RecommendReconstructSingleCommand
    using CleanMastProject.TrainMeso.RecommendTrainMesoCommand
    using CleanMastProject.ReconstructMeso.RecommendReconstructMesoCommand
    using CleanMastProject.TrainReconstructCross.RecommendTrainReconstructCrossCommand
    using CleanMastProject.ReportReconstructCross.RecommendAnalyzeReconstructCrossCommand
    using CleanMastProject.ReportReconstructCross.RecommendCrossMastReportCommand
    using CleanMastProject.ReconstructCross.RecommendReconstructCrossCommand
    using CleanMastProject.RepresentativeYear.RecommendRepresentativeYearCommand
    using CleanMastProject.WTTimeSeries.RecommendWtTimeSeriesCommand
    using CleanMastProject.ReportClean.RecommendReportCleanCommand
    using CleanMastProject.ReportRecovery.RecommendReportRecoveryCommand
    using CleanMastProject.ReportReconstructSingle.RecommendReportReconstructSingleCommand
    using CleanMastProject.ReportReconstructMeso.RecommendReportReconstructMesoCommand
    using CleanMastProject.ReportAllMasts.RecommendReportAllCommand
    using CleanMastProject.ReportTimeSeries.RecommendReportTimeSeriesMesoCommand
    using CleanMastProject.ReportTimeSeries.RecommendReportTimeSeriesRepCommand
    using CleanMastProject.ReportMesoTimeSeries.RecommendReportMesoTimeSeriesCommand

    """
    parse-sensors

    Recommend a parse-sensors.toml configuration file by scanning for data files.

    # Arguments
    - `dir`: Project directory to scan for masts/*.{csv,txt} and mesos/*.{csv,txt}

    # Example
    ```bash
    julia bin/CleanMast.jl recommend parse-sensors ./projects/my-project
    ```

    Scans the project directory for:
    - masts/*.{csv,txt} files (assumed to be NRG format)
    - mesos/*.{csv,txt} files (assumed to be freemeso-meso format)

    Generates parse-sensors.toml with default sensor format configurations.
    """
    @cast function parse_sensors(dir::String)
        RecommendParseSensorsCommand.execute(dir)
    end

    """
    process-clean

    Recommend a process-clean.toml file for the project

    # Arguments
    - `dir`: Project directory containing parse-sensors.toml
    """
    @cast function process_clean(dir::String)
        "Recommend a process-clean.toml file for the project"
        RecommendProcessCleanCommand.execute(dir)
    end
    
    """
    tower-shading

    Recommend a tower-shading.toml configuration file for the project.

    # Arguments
    - `dir`: Project directory containing config.yaml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend tower-shading ./projects/my-project
    ```

    Generates tower-shading.toml based on the project's cleaned data configuration.
    """
    @cast function tower_shading(dir::String)
        RecommendTowerShadingCommand.execute(dir)
    end
    
    """
    reconstruct-single

    Recommend a reconstruct-single.toml configuration file for the project.

    # Arguments
    - `dir`: Project directory containing tower-shading.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend reconstruct-single ./projects/my-project
    ```

    Generates reconstruct-single.toml based on the project's tower-shading configuration.
    """
    @cast function reconstruct_single(dir::String)
        RecommendReconstructSingleCommand.execute(dir)
    end
    
    """
    train-meso

    Recommend a train-meso.toml configuration file for the project.

    # Arguments
    - `dir`: Project directory containing reconstruct-single.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend train-meso ./projects/my-project
    ```

    Generates train-meso.toml for training mesoscale weather models.
    """
    @cast function train_meso(dir::String)
        RecommendTrainMesoCommand.execute(dir)
    end
    
    """
    reconstruct-meso

    Recommend a reconstruct-meso.toml configuration file for the project.

    # Arguments
    - `dir`: Project directory containing train-meso.toml

    # Options
    - `--cluster-threshold <threshold>`: Overlap threshold for mast clustering (default: 0.8)
    - `--threshold-period <days>`: Minimum intersection period for clustering (default: 120 days)

    # Example
    ```bash
    julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project
    julia bin/CleanMast.jl recommend reconstruct-meso ./projects/my-project --cluster-threshold 0.7 --threshold-period 90
    ```

    Generates reconstruct-meso.toml for reconstructing missing data using trained mesoscale models.
    When multiple masts have overlapping data, they will be clustered and share the same reconstruction period.
    """
    @cast function reconstruct_meso(
        dir::String;
        cluster_threshold::Float64=0.8,
        threshold_period::Int=120
    )
        RecommendReconstructMesoCommand.execute(dir; cluster_threshold, threshold_period)
    end
    
    """
    train-reconstruct-cross

    Recommend a train-reconstruct-cross.toml configuration file for cross-mast training.

    # Arguments
    - `dir`: Project directory containing reconstructed mast data

    # Example
    ```bash
    julia bin/CleanMast.jl recommend train-reconstruct-cross ./projects/my-project
    ```

    Generates train-reconstruct-cross.toml for training cross-mast relationships and reconstruction models.
    """
    @cast function train_reconstruct_cross(dir::String)
        RecommendTrainReconstructCrossCommand.execute(dir)
    end
    
    """
    analyze-reconstruct-cross

    Recommend an analyze-reconstruct-cross.toml configuration file for cross-mast analysis.

    # Arguments
    - `dir`: Project directory containing mast data and configurations

    # Example
    ```bash
    julia bin/CleanMast.jl recommend analyze-reconstruct-cross ./projects/my-project
    ```

    This command analyzes the project structure and generates a recommended configuration for cross-mast reconstruction analysis, including:
    - Detection of available mast data files
    - Sensor configuration analysis
    - Output directory setup for analysis results
    - Default analysis parameters for cross-mast correlation studies

    The generated analyze-reconstruct-cross.toml file can be used with:
    ```bash
    julia bin/CleanMast.jl report cross-mast path/to/analyze-reconstruct-cross.toml
    ```
    """
    @cast function analyze_reconstruct_cross(dir::String)
        RecommendAnalyzeReconstructCrossCommand.execute(dir)
    end

    """
    reconstruct-cross

    Recommend a reconstruct-cross.toml configuration file from training results.

    # Arguments
    - `train_results_path`: Path to train-reconstruct-cross results
    - `output_dir`: Output directory for the configuration file (default: "./")
    - `--min-coverage`: Minimum data coverage days for qualification (default: 30.0)

    # Example
    ```bash
    julia bin/CleanMast.jl recommend reconstruct-cross ./train-reconstruct-cross
    julia bin/CleanMast.jl recommend reconstruct-cross ./train-reconstruct-cross ./output --min-coverage 25.0
    ```

    Generates reconstruct-cross.toml for executing cross-mast reconstruction using trained models.
    """
    @cast function reconstruct_cross(train_results_path::String, output_dir::String = "./"; min_coverage::Float64 = 30.0)
        RecommendReconstructCrossCommand.execute(train_results_path, output_dir, min_coverage)
    end
    
    """
    representative-year

    Recommend a representative-year.toml configuration file for the project.

    # Arguments
    - `dir`: Project directory containing reconstruct-meso.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend representative-year ./projects/my-project
    ```

    Generates representative-year.toml for calibrating data to a representative year.
    """
    @cast function representative_year(dir::String)
        RecommendRepresentativeYearCommand.execute(dir)
    end
    
    """
    wt-timeseries

    Recommend a wt-timeseries.toml configuration file for the project.

    # Arguments
    - `dir`: Project directory containing representative-year.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend wt-timeseries ./projects/my-project
    ```

    Generates wt-timeseries.toml for processing wind turbine time series data.
    """
    @cast function wt_timeseries(dir::String)
        RecommendWtTimeSeriesCommand.execute(dir)
    end

    """
    report-clean

    Recommend a report-clean.toml configuration file for data cleaning reports.

    # Arguments
    - `dir`: Project directory containing process-clean.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-clean ./projects/my-project
    ```

    Generates report-clean.toml in report-masts/ with:
    - Raw and clean data source configurations
    - Pre-loaded cleaning rules for analysis
    - Layer difference parameters for table generation

    The generated configuration can be edited and used with:
    ```bash
    julia bin/CleanMast.jl report clean ./projects/my-project
    ```
    """
    @cast function report_clean(dir::String)
        RecommendReportCleanCommand.execute(dir)
    end

    """
    report-recovery

    Recommend a report-recovery.toml configuration file for data recovery status reports.

    # Arguments
    - `dir`: Project directory containing reconstruct-meso.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-recovery ./projects/my-project
    ```

    Generates report-recovery.toml in report-masts/ for analyzing data recovery effectiveness.
    """
    @cast function report_recovery(dir::String)
        RecommendReportRecoveryCommand.execute(dir)
    end

    """
    report-cross-mast

    Recommend a report-cross-mast.toml configuration file for cross-mast correlation reports.

    # Arguments
    - `dir`: Project directory containing reconstruct-single.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-cross-mast ./projects/my-project
    ```

    Generates report-cross-mast.toml in report-masts/ for cross-mast correlation analysis.
    """
    @cast function report_cross_mast(dir::String)
        RecommendCrossMastReportCommand.execute(dir)
    end

    """
    report-reconstruct-single

    Recommend a report-reconstruct-single.yaml configuration file for analyzing single-mast reconstruction effectiveness.

    # Arguments
    - `dir`: Project directory containing reconstruction configurations

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-reconstruct-single ./projects/my-project
    ```

    This command analyzes the project structure and generates a recommended configuration for single-mast reconstruction analysis, including:
    - Detection of tower-shading processed data (before reconstruction)
    - Detection of reconstruct-single output data (after reconstruction)
    - Configuration setup for comparing reconstruction effectiveness
    - Output directory setup under report-masts/

    The generated report-reconstruct-single.yaml file can be used with:
    ```bash
    julia bin/CleanMast.jl report reconstruct-single path/to/report-masts/report-reconstruct-single.yaml
    ```
    """
    @cast function report_reconstruct_single(dir::String)
        RecommendReportReconstructSingleCommand.execute(dir)
    end

    """
    report-reconstruct-meso

    Recommend a report-reconstruct-meso.toml configuration file for meso-mast reconstruction quality analysis.

    # Arguments
    - `dir`: Project directory containing reconstruct-meso.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-reconstruct-meso ./projects/my-project
    ```

    Generates report-reconstruct-meso.toml in report-masts/ for meso-mast reconstruction quality analysis.
    The report shows RMSE and correlation metrics for each mast-meso pair with scatter plots
    of the top 3 wind speed sensors.

    The generated configuration file can be used with:
    ```bash
    julia bin/CleanMast.jl report reconstruct-meso path/to/report-masts/report-reconstruct-meso.toml
    ```
    """
    @cast function report_reconstruct_meso(dir::String)
        RecommendReportReconstructMesoCommand.execute(dir)
    end

    """
    report-all

    Generate all report TOML configuration files for comprehensive mast analysis.

    # Arguments
    - `dir`: Project directory containing processing configurations

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-all ./projects/my-project
    ```

    This command generates all necessary TOML configuration files for the four main reports:
    1. **report-recovery.toml** - Data recovery status across reconstruction stages
    2. **report-cross-mast.toml** - Cross-mast correlation analysis configuration
    3. **report-reconstruct-single.yaml** - Single-mast reconstruction effectiveness analysis

    The configurations are saved to the `report-masts/` directory and can then be used with:
    ```bash
    julia bin/CleanMast.jl report all ./projects/my-project
    ```

    Requirements:
    - `reconstruct-meso.toml` (for recovery report config)
    - `reconstruct-single.toml` (for cross-mast report config)
    - `tower-shading.toml` (for reconstruct-single report config)
    - `process-clean.toml` (used directly by clean report)
    - `representative-year.toml` (used directly by representative year report)
    """
    @cast function report_all(dir::String)
        RecommendReportAllCommand.execute(dir)
    end

    """
    report-timeseries-meso

    Generate report-timeseries-meso.toml configuration for time series analysis of meso-reconstructed data.

    # Arguments
    - `dir`: Project directory containing reconstruct-meso.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-timeseries-meso ./projects/my-project
    ```

    This command reads reconstruct-meso.toml and generates a configuration for time series analysis
    of the meso-reconstructed data output. The configuration will be saved as:
    `report-masts/report-timeseries-meso.toml`

    Use the generated configuration with:
    ```bash
    julia bin/CleanMast.jl report timeseries ./projects/my-project/report-masts/report-timeseries-meso.toml
    ```
    """
    @cast function report_timeseries_meso(dir::String)
        RecommendReportTimeSeriesMesoCommand.execute(dir)
    end

    """
    report-timeseries-rep

    Generate report-timeseries-rep.toml configuration for time series analysis of representative year data.

    # Arguments
    - `dir`: Project directory containing representative-year.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-timeseries-rep ./projects/my-project
    ```

    This command reads representative-year.toml and generates a configuration for time series analysis
    of the representative year data output. The configuration will be saved as:
    `report-masts/report-timeseries-rep.toml`

    Use the generated configuration with:
    ```bash
    julia bin/CleanMast.jl report timeseries ./projects/my-project/report-masts/report-timeseries-rep.toml
    ```
    """
    @cast function report_timeseries_rep(dir::String)
        RecommendReportTimeSeriesRepCommand.execute(dir)
    end

    """
    report-meso-timeseries

    Generate report-meso-timeseries.toml configuration for annual climatology analysis of meso data.

    # Arguments
    - `dir`: Project directory containing parse-sensors.toml

    # Example
    ```bash
    julia bin/CleanMast.jl recommend report-meso-timeseries ./projects/my-project
    ```

    This command reads parse-sensors.toml to find meso data sources with output configurations
    and generates a configuration for annual climatology analysis. The configuration will be saved as:
    `report-masts/report-meso-timeseries.toml`

    The analysis will:
    - Use the highest wind speed sensor for each meso dataset
    - Calculate annual mean wind speeds for each year
    - Compute climatology (multi-year average)
    - Generate tables and plots showing interannual variability

    Requirements:
    - parse-sensors.toml must exist in the project directory
    - Meso datasets in parse-sensors.toml must have 'output' fields defined

    Use the generated configuration with:
    ```bash
    julia bin/CleanMast.jl report meso-timeseries ./projects/my-project/report-masts/report-meso-timeseries.toml
    ```
    """
    @cast function report_meso_timeseries(dir::String)
        RecommendReportMesoTimeSeriesCommand.execute(dir)
    end
end

"""
analyze

Analysis and reporting commands
"""
Comonicon.@cast module Analyze
    using Comonicon
    using CleanMastProject.Command.AnalyzeEN
    using CleanMastProject.ReportReconstructCross.CommandReportReconstructCross


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



end

"""
report

Report generation commands
"""
Comonicon.@cast module Report
    using Comonicon
    using CleanMastProject.ReportClean.ReportAllCommand
    using CleanMastProject.ReportAllMasts.ReportAllMastsCommand
    using CleanMastProject.ReportRecovery.RecommendReportRecoveryCommand
    using CleanMastProject.ReportRecovery.ReportRecoveryCommand
    using CleanMastProject.RepresentativeYear.ReportRepresentativeYearCommand
    using CleanMastProject.ReportReconstructCross.CommandReportReconstructCross
    using CleanMastProject.ReportTimeSeries.ReportTimeSeriesCommand
    using CleanMastProject.ReportReconstructSingle.ReportReconstructSingleCommand
    using CleanMastProject.ReportReconstructMeso.CommandReportReconstructMeso
    using CleanMastProject.ReportMesoTimeSeries.ReportMesoTimeSeriesCommand

    """
    clean

    Generate process clean report from configuration file.

    # Arguments
    - `config_path`: Path to report-clean.toml configuration file

    # Example
    ```bash
    # Step 1: Generate configuration
    julia bin/CleanMast.jl recommend report-clean ./projects/my-project

    # Step 2: Generate report from configuration
    julia bin/CleanMast.jl report clean ./projects/my-project/report-masts/report-clean.toml
    ```

    This command:
    1. Loads report-clean.toml configuration file
    2. Loads raw and clean data files (paths relative to config location)
    3. Loads violation summaries from process-stats/
    4. Generates Chinese Typst report with:
       - Executive summary (执行摘要)
       - Sensor inventory (传感器清单)
       - Data coverage comparison (数据覆盖率对比)
       - Rule violations analysis (规则违规分析)

    Output:
    - report-masts/clean/report.typ: Main Chinese report
    - report-masts/clean/generation.log: Generation log
    - report-masts/clean/generation.err: Error log
    - report-masts/clean/plots/: Generated plots

    Note: You must run 'recommend report-clean' first to generate the configuration.
    """
    Comonicon.@cast function clean(config_path::String)
        ReportCleanCommand.execute(config_path)
    end

    """
    all

    Generate all comprehensive mast reports for a project.

    # Arguments
    - `project_dir`: Path to project directory containing configurations

    # Example
    ```bash
    julia bin/CleanMast.jl report all ./projects/my-project
    ```

    This command generates four comprehensive reports:

    1. **Clean Report** - Raw vs clean data comparison with violation analysis
    2. **Recovery Report** - Data coverage across reconstruction stages
    3. **Cross-Mast Report** - Correlation analysis between mast pairs
    4. **Representative Year Report** - Calibration analysis and effectiveness

    Requirements:
    - process-clean.toml (for clean report)
    - reconstruct-meso.toml (for recovery report)
    - analyze-reconstruct-cross.toml (for cross-mast report)
    - representative-year.toml (for representative year report)

    Output:
    - report-masts/clean/report.typ: Clean data analysis
    - report-masts/recovery/recovery-report.typ: Reconstruction effectiveness
    - report-masts/cross-mast/report.typ: Cross-mast correlation analysis
    - report-masts/representative-year/report.typ: Calibration analysis

    The command continues with available reports if some configurations are missing.
    """
    Comonicon.@cast function all(project_dir::String)
        ReportAllMastsCommand.execute(project_dir)
    end

    """
    recovery

    Generate data recovery status report showing reconstruction effectiveness.

    # Arguments
    - `config_path`: Path to report-recovery.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl report recovery ./projects/my-project/report-masts/report-recovery.toml
    ```

    This command:
    1. Loads report-recovery.toml configuration
    2. Analyzes data at each reconstruction stage:
       - Tower shading (initial processed data)
       - Single-mast reconstruction
       - Cross-mast reconstruction
       - Mesoscale reconstruction
    3. Calculates recovery statistics for each sensor
    4. Generates Chinese Typst report with:
       - Recovery tables for each mast (恢复统计表)
       - Bar charts showing reconstruction effectiveness
       - Overall recovery summary (总体恢复统计)

    Output:
    - report-masts/recovery/recovery-report.typ: Main Chinese report
    - Tables showing: 初始缺失, 同塔插补, 异塔插补, 中尺度插补, 最终缺失
    - Bar charts with dodge categories for each reconstruction type
    """
    Comonicon.@cast function recovery(config_path::String)
        ReportRecoveryCommand.execute(config_path)
    end

    """
    representative-year

    Generate representative year calibration analysis report.

    # Arguments
    - `project_dir`: Path to project directory containing representative-year.toml

    # Example
    ```bash
    julia bin/CleanMast.jl report representative-year ./projects/my-project
    ```

    This command:
    1. Loads representative-year.toml configuration  
    2. Analyzes calibration results for each mast-meso pair:
       - Climatology vs training period comparison
       - Representative year selection and effectiveness
       - 16-sector detailed analysis with slopes and intercepts
    3. Filters sensor analysis to ≥100m height or highest available
    4. Generates comprehensive Chinese/English Typst report with:
       - Executive summary (执行摘要)
       - Climatology analysis (气候学分析)  
       - 16-sector performance tables (16方向扇区分析)
       - Sensor calibration status (传感器校正分析)
       - Performance metrics and recommendations

    Output:
    - representative-year-report/report.typ: Main bilingual report
    - representative-year-report/tables/: Individual analysis tables
    - representative-year-report/data/: CSV data exports
    
    Requirements:
    - representative-year.toml configuration file
    - Calibration results in process-stats/ (if calibration was applied)
    - Meso data sources for climatology analysis
    """
    Comonicon.@cast function representative_year(project_dir::String)
        ReportRepresentativeYearCommand.execute(project_dir)
    end

    """
    cross-mast

    Generate cross-mast correlation analysis reports.

    # Arguments
    - `config_path`: Path to report-cross-mast.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl report cross-mast path/to/report-cross-mast.toml
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
    Comonicon.@cast function cross_mast(config_path::String)
        CommandReportReconstructCross.execute(config_path)
    end

    """
    timeseries

    Generate time series analysis reports using an analyze configuration file.

    # Arguments
    - `config_path`: Path to analyze configuration file (supports .yaml, .toml, .json)

    # Examples
    ```bash
    julia bin/CleanMast.jl report timeseries path/to/analyze.yaml
    julia bin/CleanMast.jl report timeseries path/to/analyze.toml
    julia bin/CleanMast.jl report timeseries path/to/analyze.json
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
        ReportTimeSeriesCommand.execute(config_path)
    end

    """
    reconstruct-single

    Generate report comparing time series data before and after single mast reconstruction.

    # Arguments
    - `config_path`: Path to analyze-reconstruct-single.yaml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl report reconstruct-single path/to/analyze-reconstruct-single.yaml
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
        ReportReconstructSingleCommand.execute(config_path)
    end

    """
    reconstruct-meso

    Generate meso-mast reconstruction quality analysis report.

    # Arguments
    - `config_path`: Path to report-reconstruct-meso.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl report reconstruct-meso path/to/report-masts/report-reconstruct-meso.toml
    ```

    The TOML configuration file should specify:
    - Multiple masts with their input data files and meso source names
    - Multiple meso data sources
    - Analysis settings including output directory and plot preferences

    For each mast-meso pair, generates:
    - RMSE (Root Mean Square Error) metrics
    - Pearson correlation coefficients
    - Scatter plots with fitted regression lines for top 3 wind speed sensors (statType = avg)
    - CSV data exports for further analysis
    - Comprehensive Chinese Typst report with embedded visualizations

    Output includes:
    - report.typ: Main Chinese report with all analysis results
    - plots/: Individual plot files ({mast}_{meso}_sensors.png)
    - data/: CSV exports ({mast}_{meso}_metrics.csv)
    """
    Comonicon.@cast function reconstruct_meso(config_path::String)
        CommandReportReconstructMeso.execute(config_path)
    end

    """
    meso-timeseries

    Generate meso-timeseries annual climatology analysis report.

    # Arguments
    - `config_path`: Path to report-meso-timeseries.toml configuration file

    # Example
    ```bash
    julia bin/CleanMast.jl report meso-timeseries path/to/report-masts/report-meso-timeseries.toml
    ```

    The TOML configuration file should specify:
    - Multiple meso datasets with their data files and sensor configurations
    - Output directory for results

    For each meso dataset, generates:
    - Annual wind speed climatology analysis using the highest sensor
    - CSV table with annual means, climatology, and differences
    - SVG plot showing annual timeseries with climatology line
    - Typst report with summary statistics

    Output includes:
    - annual_climatology.typ: Main Chinese report with analysis results
    - annual_climatology.csv: Data table with annual statistics
    - annual_climatology.svg: Visualization plot
    """
    Comonicon.@cast function meso_timeseries(config_path::String)
        ReportMesoTimeSeriesCommand.execute(config_path)
    end

end

"""
CleanMast - Wind measurement data cleaning and analysis tool

A command-line tool for processing wind measurement data.
"""
Comonicon.@main

end # module CleanMastCli
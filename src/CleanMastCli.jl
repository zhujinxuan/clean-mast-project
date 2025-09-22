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
    using CleanMastProject.AnalyzeReconstructCross.RecommendCrossMastReportCommand
    using CleanMastProject.ReconstructCross.RecommendReconstructCrossCommand
    using CleanMastProject.RepresentativeYear.RecommendRepresentativeYearCommand
    using CleanMastProject.WTTimeSeries.RecommendWtTimeSeriesCommand
    using CleanMastProject.ReportRecovery.RecommendReportRecoveryCommand

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

    @cast function report_recovery(dir::String)
        "Recommend a report-recovery.toml file for data recovery status report (saved to report-masts/)"
        RecommendReportRecoveryCommand.execute(dir)
    end

    @cast function report_cross_mast(dir::String)
        "Recommend a report-cross-mast.toml file for cross-mast report (saved to report-masts/)"
        RecommendCrossMastReportCommand.execute(dir)
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


end

"""
calculate

Calculation and utility commands
"""
Comonicon.@cast module Calculate
    using Comonicon
    using CleanMastProject.Command.CalculateAirDensityCommand

    """
    ad

    Calculate air density from temperature and pressure data in a CSV file.

    # Arguments
    - `csv_path`: Path to CSV file containing temperature and pressure data
    - `--temp-col`: Name of temperature column (assumed to be in Celsius)
    - `--pressure-col`: Name of pressure column (assumed to be in Pascals)

    # Example
    ```bash
    julia bin/CleanMast.jl calculate ad data.csv --temp-col Temperature_80m_avg --pressure-col Pressure_80m_avg
    ```

    The command calculates air density using:
    1. Median temperature and pressure values from the specified columns
    2. Ideal gas law for dry air: ρ = P / (R_specific × T)
    3. Results are displayed with comparison to standard conditions
    """
    Comonicon.@cast function ad(csv_path::String; temp_col::String, pressure_col::String)
        CalculateAirDensityCommand.execute(csv_path, temp_col, pressure_col)
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
    using CleanMastProject.AnalyzeReconstructCross.CommandAnalyzeReconstructCross

    """
    clean

    Generate process clean report for a project.

    # Arguments
    - `project_dir`: Path to project directory containing process-clean.toml

    # Example
    ```bash
    julia bin/CleanMast.jl report clean ./projects/my-project
    ```

    This command:
    1. Reads process-clean.toml configuration
    2. Generates report configuration automatically
    3. Loads raw and clean data files
    4. Loads violation summaries from process-stats/
    5. Generates Chinese Typst report with:
       - Executive summary (执行摘要)
       - Sensor inventory (传感器清单)
       - Data coverage comparison (数据覆盖率对比)
       - Rule violations analysis (规则违规分析)

    Output:
    - report-masts/clean/report.typ: Main Chinese report
    - report-masts/clean/generation.log: Generation log
    - report-masts/clean/generation.err: Error log
    - report-masts/clean/plots/: Generated plots
    """
    Comonicon.@cast function clean(project_dir::String)
        ReportAllCommand.execute(project_dir)
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
        CommandAnalyzeReconstructCross.execute(config_path)
    end

end

"""
CleanMast - Wind measurement data cleaning and analysis tool

A command-line tool for processing wind measurement data.
"""
Comonicon.@main

end # module CleanMastCli
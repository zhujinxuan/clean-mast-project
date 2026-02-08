# 文件：./test/runtests.jl

using Test
using Pkg

# Get absolute path of test directory
test_dir = @__DIR__
project_dir = joinpath(test_dir, "..")

# Activate project environment
Pkg.activate(project_dir)

# Define test sets and their corresponding files
const TEST_SETS = Dict{String, Vector{String}}(
    "parse_sensors" => [
        "ParseSensors/test_column_parser.jl",
        "ParseSensors/test_dataframe_processor.jl",
        "ParseSensors/test_file_processor.jl",
        "ParseSensors/test_command_parse_sensors.jl",
        "ParseSensors/test_interpolation_config.jl"
    ],
    "data-clean" => [
        "DataClean/test_range_rules.jl",
        "DataClean/test_icing_rules.jl",
        "DataClean/test_layer_diff_rules.jl",
        "DataClean/test_availability_rules.jl"
    ],
    "process" => ["process/test_apply_missing.jl"],
    "tower" => ["TowerShading/TowerShading.jl"],
    "sector" => ["test_sector.jl"],
    "sensor_naming" => ["test_sensor_naming.jl"],
    "time_series_processing" => [
        "TimeSeriesProcessing/test_time_series_processing.jl",
        "TimeSeriesProcessing/test_interval_detection.jl",
        "TimeSeriesProcessing/test_mast_timeseries_path_utils.jl"
    ],
    "measurement_period" => [
        "TimeSeriesProcessing/test_measurement_period_calculator.jl",
        "TimeSeriesProcessing/test_mast_period_alignment.jl"
    ],
    "single_mast" => [
        "ReconstructSingleMast/test_apply_reconstruction.jl",
        "ReconstructSingleMast/test_group_by_hour.jl",
        "ReconstructSingleMast/test_layer_selection.jl",
        "ReconstructSingleMast/test_wind_speed_reconstruct_hourly.jl",
        "ReconstructSingleMast/test_wind_direction_reconstruct_hourly.jl"
    ],
    "representative_year" => [
        "RepresentativeYear/test_utils.jl",
        "RepresentativeYear/test_analysis.jl",
        "RepresentativeYear/test_recommend_command.jl"
    ],
    "guess_mast_from_meso" => ["GuessMastFromMeso/test_guess_mast.jl"],
    "wind_models" => [
        "WindModels/test_sectorized_regression_training.jl",
        "WindModels/test_direction_offset_training.jl"
    ],
    "train_reconstruct_cross" => [
        "TrainReconstructCross/test_data_coverage.jl",
        "TrainReconstructCross/test_cross_mast_speed_correlation.jl",
        "TrainReconstructCross/test_cross_mast_direction_analysis.jl",
        "TrainReconstructCross/test_cross_mast_summary.jl"
    ],
    "reconstruct_cross" => [
        "ReconstructCross/test_append_new_timestamps.jl",
        "ReconstructCross/test_reconstruct_cross_batching.jl"
    ],
    "logging" => [
        "logging/test_utils.jl",
        "logging/test_log_rotation.jl",
        "logging/test_jsonl_logger.jl",
        "logging/test_terminal_formatter.jl",
        "logging/test_integration.jl",
        "logging/test_worker_logger_manager.jl",
        "logging/test_parallel_logging.jl"
    ],
    "turbulence" => [
        "ReportTimeSeries/test_turbulence_nan_fix.jl"
    ],
    "wind_rose" => [
        "ReportTimeSeries/test_wind_rose_directions.jl"
    ],
    "types" => [
        "Types/test_process_clean_config_utils.jl",
        "Types/test_parquet_io.jl"
    ],
    "pandoc_utils" => [
        "PandocUtils/test_pandoc_utils.jl"
    ],
    "report_frozen_period" => [
        "ReportFrozenPeriod/test_period_operations.jl",
        "ReportFrozenPeriod/test_component_detection.jl",
        "ReportFrozenPeriod/test_missing_data_stats.jl"
    ],
    "report_utils" => [
        "test_report_utils.jl"
    ]
)

# Helper function to list available test sets
function print_available_test_sets()
    println("Available test sets:")
    for (name, files) in sort(collect(TEST_SETS))
        println("  $name:")
        for file in files
            println("    - $file")
        end
    end
end

# Parse command line arguments
function parse_args()
    if isempty(ARGS)
        return collect(keys(TEST_SETS))  # Run all tests if no arguments
    elseif ARGS[1] in ["--help", "-h"]
        println("Usage: julia runtests.jl [test_set1 test_set2 ...]")
        println("Run specific test sets. If no test set is specified, runs all tests.")
        println()
        print_available_test_sets()
        exit(0)
    else
        # Validate test set names
        invalid_sets = setdiff(ARGS, keys(TEST_SETS))
        if !isempty(invalid_sets)
            println("Error: Invalid test sets: ", join(invalid_sets, ", "))
            println()
            print_available_test_sets()
            exit(1)
        end
        return ARGS
    end
end

# Run selected test sets
function run_test_sets(selected_sets)
    for test_set in selected_sets
        files = TEST_SETS[test_set]
        @testset "$test_set" begin
            for file in files
                include(file)
            end
        end
    end
end

# Main execution
selected_sets = parse_args()
run_test_sets(selected_sets)

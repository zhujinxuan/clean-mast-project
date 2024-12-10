using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries
using CleanMastProject.ReconstructSingleMast.WindSpeedTraining
using CleanMastProject.MastTimeSeries
using CleanMastProject.Types.ReconstructSingleMast

function generate_synthetic_wind_data(;
    start_date::DateTime = DateTime(2024,1,1),
    duration_days::Int = 1,
    time_step::Period = Minute(10),
    heights::Vector{Float64} = [50.0, 80.0, 100.0, 120.0, 160.0],
    base_ws::Float64 = 5.0,
    amplitude::Float64 = 2.0
)
    # Generate timestamps
    timestamps = start_date:time_step:(start_date + Day(duration_days) - time_step)
    n_points = length(timestamps)
    
    # Convert hours to floating point to avoid integer division issues
    milliseconds_since_start = Float64.(Dates.value.(Millisecond.(timestamps .- start_date)))
    hours_since_start = milliseconds_since_start / (60 * 60 * 1000)  # Convert milliseconds to hours
    
    # Generate base wind speeds at reference height (50m)
    base_winds = [
        base_ws + amplitude * sin(2π * h / 24) for h in hours_since_start
    ]
    
    # Generate random shear exponents for each hour
    # We'll interpolate between hourly values for 10-min data
    hourly_alphas = rand(24 * duration_days) .* 0.75 .- 0.25  # Range: -0.25 to 0.5
    
    # Interpolate alpha values for each timestamp
    alpha_indices = hours_since_start .+ 1
    floor_indices = floor.(Int, alpha_indices)
    ceil_indices = ceil.(Int, alpha_indices)
    weights = alpha_indices .- floor_indices
    
    alphas = [
        (1-w) * hourly_alphas[min(fi, length(hourly_alphas))] + 
        w * hourly_alphas[min(ci, length(hourly_alphas))]
        for (w, fi, ci) in zip(weights, floor_indices, ceil_indices)
    ]
    
    # Calculate wind speeds at all heights using power law
    ref_height = heights[1]
    df = DataFrame(
        :timestamp => collect(timestamps),
        [Symbol("ws_$(Int(height))m") => Vector{Union{Missing, Float64}}(missing, n_points) for height in heights]...
    )
    
    for height in heights
        col_name = Symbol("ws_$(Int(height))m")
        df[!, col_name] = [
            base_wind * (height/ref_height)^alpha
            for (base_wind, alpha) in zip(base_winds, alphas)
        ]
    end
    
    return df
end

function create_test_data()::TimeSeriesData
    df = generate_synthetic_wind_data()

    sensors = [
      SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
      for h in [50.0, 80.0, 100.0, 120.0, 160.0]
    ]

    TimeSeriesData(df, sensors)
end

@testset "WindSpeedTraining" begin
    @testset "calculate_hourly_averages" begin
        data = create_test_data()
        hour_start = DateTime(2024,1,1)
        heights_speeds = calculate_hourly_averages(data.df, hour_start, data.sensors)
        
        @test length(heights_speeds) == 5
        @test all(x -> first(x) ∈ [50.0, 80.0, 100.0, 120.0, 160.0], heights_speeds)
        @test all(x -> typeof(last(x)) <: Float64, heights_speeds)
    end

    @testset "calculate_wind_shear_profile with known alpha" begin
        # Generate heights_speeds using power law with alpha = 0.20
        reference_height = 50.0
        reference_speed = 5.0
        alpha = 0.20
        
        heights = [50.0, 80.0, 100.0, 120.0]
        profile = WindSpeedProfile(50.0, 0.2)  # Example profile
        heights_speeds = map(h -> 
            (h, apply_wind_shear_profile(profile, reference_speed, h))
        , heights)
        
        profile = calculate_wind_shear_profile(heights_speeds)
        
        @test !isnothing(profile)
        @test abs(profile.shear_exponent - alpha) < 0.01
        @test profile.reference_height == DEFAULT_REFERENCE_HEIGHT
    end

    @testset "apply_wind_shear_profile" begin
        profile = WindSpeedProfile(50.0, 0.2)  # Example profile
        reference_speed = 5.0
        target_height = 80.0
        
        result = apply_wind_shear_profile(profile, reference_speed, target_height)
        @test result > reference_speed  # Higher height should give higher speed
    end

    # @testset "reconstruct_wind_speeds integration" begin
    #     data = create_test_data()
    #     successes, failures = reconstruct_wind_speeds(data)
        
    #     @test !isempty(successes)
    #     @test all(s -> s isa ReconstructedSuccess, successes)
    #     @test all(f -> f isa ReconstructedFailure, failures)
        
    #     # Check that we got reconstructions for missing values
    #     missing_timestamps = [DateTime(2024,1,1) + Hour(2), 
    #                         DateTime(2024,1,1) + Hour(3),
    #                         DateTime(2024,1,1) + Hour(4)]
    #     @test all(s -> s.timestamp in missing_timestamps, successes)
    # end

end 
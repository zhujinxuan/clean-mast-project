using Test
using DataFrames
using Dates
using StatsBase: countmap
using CleanMastProject.ReconstructSingleMast.DirectionTraining
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.ReconstructSingleMast
using CleanMastProject.Types.Sector: abs_degree_diff
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.ReconstructSingleMast.DirectionTraining: get_speeds_for_averaging

function create_test_data_for_vector_average()::TimeSeriesData
    timestamps = DateTime(2024,1,1):Minute(10):DateTime(2024,1,2)
    directions = [45.0 for _ in 1:length(timestamps)]
    speeds = Vector{Union{Missing, Float64}}([rand(3.0:0.1:5.0) for _ in 1:length(timestamps)])
    
    # Introduce missing values
    n_missing = round(Int, 0.2 * length(speeds))
    missing_indices = rand(1:length(speeds), n_missing)
    speeds[missing_indices] .= missing
    directions[missing_indices] .= 270.0

    df = DataFrame(
        :timestamp => timestamps,
        :direction => directions,
        :speed => speeds
    )

    sensors = [
        SensorColumn(:direction, "WindDirection", "N", 98.0, "avg", "deg"),
        SensorColumn(:speed, "WindSpeed", "N", 100.0, "avg", "m/s")
    ]

    TimeSeriesData(df, sensors)
end


@testset "DirectionTraining" begin
    @testset "direction_to_vector and vector_to_direction" begin
        direction = 45.0
        x, y = direction_to_vector(direction)
        
        @test x ≈ sqrt(2)/2 atol=1e-6
        @test y ≈ sqrt(2)/2 atol=1e-6
        
        reconstructed = vector_to_direction(x, y)
        @test reconstructed ≈ direction atol=1e-6
    end

    @testset "Vector Average Test" begin
        data = create_test_data_for_vector_average()
        direction_sensor = first(filter(s -> s.sensorType == "WindDirection", data.sensors))
        speed_sensor = first(filter(s -> s.sensorType == "WindSpeed", data.sensors))
        
        result = calculate_vector_average(data, direction_sensor, speed_sensor)
        @test !isnothing(result)
        
        # Extract the direction from the result
        average_direction, speed = result
        
        # Test if the average direction is approximately 45 degrees
        @test average_direction ≈ 45.0 atol=1e-6
        @test speed ≈ 4.0 atol=2
    end
end 

function create_test_layered_data(
    start_time::DateTime = DateTime(2024,1,1),
    end_time::DateTime = DateTime(2024,1,2)
)::TimeSeriesData
    # Define time steps (10-minute intervals)
    timestamps = start_time:Minute(10):end_time
    n_points = length(timestamps)
    
    # Calculate hours for direction differences
    hour_indices = floor.(Int, range(0, n_points-1) ./ 6) .+ 1  # 6 points per hour
    n_hours = length(unique(hour_indices))
    
    # Generate base directions that change slowly over time (more realistic)
    # Start with a random direction and add small changes
    base_direction = rand() * 360
    base_directions = zeros(n_points)
    base_directions[1] = base_direction
    
    # Add small random changes (max 5 degrees per 10 minutes)
    for i in 2:n_points
        change = (rand() - 0.5) * 10  # Random change between -5 and 5 degrees
        base_directions[i] = mod(base_directions[i-1] + change, 360)
    end
    
    # Generate hourly direction differences (random between -5 and 5 degrees)
    # This is more realistic for 20m height difference
    hourly_diffs = (rand(n_hours) .- 0.5) * 10.0
    
    # Create direction arrays with realistic variations
    directions_98m = base_directions
    directions_118m = map(1:n_points) do i
        # Add some noise to make it more realistic
        hour_diff = hourly_diffs[hour_indices[i]]
        noise = (rand() - 0.5) * 2  # Small random noise ±1 degree
        mod(base_directions[i] + hour_diff + noise, 360)
    end
    
    # Generate wind speeds with realistic shear
    speeds_100m = rand(n_points) .* 2 .+ 3  # Random between 3-5
    speeds_120m = speeds_100m .* (120/100)^0.2  # Typical shear exponent of 0.2
    
    # Create DataFrame
    df = DataFrame(
        :timestamp => timestamps,
        :direction_98m => directions_98m,
        :direction_118m => directions_118m,
        :speed_100m => speeds_100m,
        :speed_120m => speeds_120m
    )
    
    # Define sensors
    sensors = [
        SensorColumn(:direction_98m, "WindDirection", "N", 98.0, "avg", "deg"),
        SensorColumn(:direction_118m, "WindDirection", "N", 118.0, "avg", "deg"),
        SensorColumn(:speed_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
        SensorColumn(:speed_120m, "WindSpeed", "N", 120.0, "avg", "m/s")
    ]
    
    TimeSeriesData(df, sensors)
end

function create_masked_layered_data(
    data::TimeSeriesData;
    direction_mask_fraction::Float64 = 0.1,
    speed_mask_fraction::Float64 = 0.1
)::TimeSeriesData
    # Deep copy the data and convert columns to allow missing values
    masked_df = deepcopy(data.df)
    masked_df[!, :direction_118m] = Vector{Union{Float64, Missing}}(masked_df.direction_118m)
    masked_df[!, :speed_100m] = Vector{Union{Float64, Missing}}(masked_df.speed_100m)
    masked_df[!, :speed_120m] = Vector{Union{Float64, Missing}}(masked_df.speed_120m)
    
    # Get number of points to mask
    n_points = nrow(masked_df)
    n_direction_mask = round(Int, n_points * direction_mask_fraction)
    n_speed_mask = round(Int, n_points * speed_mask_fraction)
    
    # Mask direction at 118m, but ensure we don't mask consecutive points
    n_hours = ceil(Int, n_points / 6)  # 6 points per hour
    available_indices = Set(1:n_points)
    direction_mask_indices = Int[]
    
    # Mask one point per hour at most
    for hour in 1:n_hours
        hour_start = (hour - 1) * 6 + 1
        hour_end = min(hour * 6, n_points)
        hour_indices = collect(hour_start:hour_end)
        
        # Only mask if we haven't reached our target and have available indices
        if length(direction_mask_indices) < n_direction_mask && !isempty(intersect(Set(hour_indices), available_indices))
            # Choose one random index from this hour
            valid_indices = collect(intersect(Set(hour_indices), available_indices))
            idx = rand(valid_indices)
            push!(direction_mask_indices, idx)
            
            # Remove this index and adjacent ones from available indices
            delete!(available_indices, idx)
            idx > 1 && delete!(available_indices, idx-1)
            idx < n_points && delete!(available_indices, idx+1)
        end
    end
    
    # Apply masks
    masked_df[direction_mask_indices, :direction_118m] .= missing
    
    # Mask speeds at both heights, using similar strategy
    for speed_col in [:speed_100m, :speed_120m]
        available_indices = Set(1:n_points)
        speed_mask_indices = Int[]
        
        for hour in 1:n_hours
            hour_start = (hour - 1) * 6 + 1
            hour_end = min(hour * 6, n_points)
            hour_indices = collect(hour_start:hour_end)
            
            if length(speed_mask_indices) < n_speed_mask && !isempty(intersect(Set(hour_indices), available_indices))
                valid_indices = collect(intersect(Set(hour_indices), available_indices))
                idx = rand(valid_indices)
                push!(speed_mask_indices, idx)
                
                delete!(available_indices, idx)
                idx > 1 && delete!(available_indices, idx-1)
                idx < n_points && delete!(available_indices, idx+1)
            end
        end
        
        masked_df[speed_mask_indices, speed_col] .= missing
    end
    
    TimeSeriesData(masked_df, data.sensors)
end


@testset "Direction Reconstruction Accuracy" begin
    # Create original and masked data
    original_data = create_test_layered_data()
    masked_data = create_masked_layered_data(original_data)
    
    # Print data info before reconstruction
    
    # Perform reconstruction
    successes, failures = reconstruct_wind_directions(masked_data)
    
    
    @testset "Reconstruction Results" begin
        # Test that we have some successful reconstructions
        @test !isempty(successes)
        # Test reconstruction rate
        total_missing = count(ismissing, masked_data.df.direction_118m)
        reconstruction_rate = length(successes) / total_missing
        
        # Using do-block for computed message
        message = "Only $(round(reconstruction_rate * 100, digits=1))% of values were reconstructed"
        @test reconstruction_rate ≥ 0.95 
        
        # Compare reconstructed values with original values
        for success in successes
            original_value = original_data.df[
                original_data.df.timestamp .== success.timestamp, 
                success.columnName
            ][1]
            
            diff = abs_degree_diff(success.value, original_value)
            
            @test abs(diff) ≤ 15.0 
        end
    end
end

@testset "get_speeds_for_averaging" begin
    # Test with no speed sensor
    df = DataFrame(:timestamp => [now()], :speed => [10.0])
    speeds = get_speeds_for_averaging(df, nothing)
    @test all(speeds .== 1.0)
    @test length(speeds) == 1
    
    # Test with all valid speeds
    speed_sensor = SensorColumn(:speed, "WindSpeed", "N", 100.0, "avg", "m/s")
    df = DataFrame(:timestamp => [now(), now()], :speed => [10.0, 20.0])
    speeds = get_speeds_for_averaging(df, speed_sensor)
    @test speeds == [10.0, 20.0]
    
    # Test with some missing speeds
    df = DataFrame(:timestamp => [now(), now(), now()], 
                  :speed => [10.0, missing, 20.0])
    speeds = get_speeds_for_averaging(df, speed_sensor)
    @test speeds ≈ [10.0, 15.0, 20.0]  # 15.0 is mean of 10.0 and 20.0
    
    # Test with all missing speeds
    df = DataFrame(:timestamp => [now(), now()], 
                  :speed => [missing, missing])
    speeds = get_speeds_for_averaging(df, speed_sensor)
    @test all(speeds .== 1.0)
    @test length(speeds) == 2
end
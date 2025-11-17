# Generates Ch2/Ch7 duplicate sensor scenario with 0% overlap
# Simulates sensor replacement: Ch2 fails, Ch7 replaces it

using DataFrames, Dates

"""
Generate test data for Ch2/Ch7 sensor replacement with zero overlap.
- Ch2: rows 1-100 have data (sensor was working)
- Ch7: rows 101-200 have data (replacement sensor)
- 0% overlap - perfect replacement scenario
"""
function generate_input_data()
    total_rows = 200
    timestamps = [DateTime(2024, 1, 1) + Minute(10 * (i-1)) for i in 1:total_rows]

    # Ch2 data: first 100 rows only
    ch2_data = vcat(
        rand(100) .* 5 .+ 3,  # Wind speeds 3-8 m/s
        fill(missing, 100)
    )

    # Ch7 data: last 100 rows only
    ch7_data = vcat(
        fill(missing, 100),
        rand(100) .* 5 .+ 3  # Wind speeds 3-8 m/s
    )

    return DataFrame(
        timestamp = timestamps,
        Symbol("Ch2_Anem_120.00m_SE_Avg_m/s") = ch2_data,
        Symbol("Ch7_Anem_120.00m_SE_Avg_m/s") = ch7_data
    )
end

# Generates Ch2/Ch7 duplicate sensor scenario with 15% overlap
# Should trigger warning (>10% overlap)

using DataFrames, Dates

"""
Generate test data for Ch2/Ch7 with 15% overlap.
- Ch2: rows 1-120 have data
- Ch7: rows 101-200 have data
- Overlap: rows 101-120 (20/200 = 10% of total, but 20/120 = 16.7% of Ch2)
- Should trigger warning
"""
function generate_input_data()
    total_rows = 200
    timestamps = [DateTime(2024, 1, 1) + Minute(10 * (i-1)) for i in 1:total_rows]

    # Ch2 data: rows 1-120
    ch2_data = vcat(
        rand(120) .* 5 .+ 3,
        fill(missing, 80)
    )

    # Ch7 data: rows 101-200
    ch7_data = vcat(
        fill(missing, 100),
        rand(100) .* 5 .+ 3
    )

    return DataFrame(
        timestamp = timestamps,
        Symbol("Ch2_Anem_120.00m_SE_Avg_m/s") = ch2_data,
        Symbol("Ch7_Anem_120.00m_SE_Avg_m/s") = ch7_data
    )
end

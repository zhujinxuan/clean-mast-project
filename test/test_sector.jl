module TestSector

using Test
using CleanMastProject.Types.Sector: get_direction_sector, DirectionSector, abs_degree_diff, degree_diff

@testset "DirectionSector" begin
    @testset "get_direction_sector" begin
        # Test exact sector centers
        @test get_direction_sector(0.0).name == "N"
        @test get_direction_sector(45.0).name == "NE"
        @test get_direction_sector(90.0).name == "E"
        @test get_direction_sector(135.0).name == "SE"
        @test get_direction_sector(180.0).name == "S"
        @test get_direction_sector(225.0).name == "SW"
        @test get_direction_sector(270.0).name == "W"
        @test get_direction_sector(315.0).name == "NW"
        
        # Test sector boundaries
        @test get_direction_sector(11.24).name == "N"
        @test get_direction_sector(11.26).name == "NNE"
        @test get_direction_sector(348.8).name == "N"
        
        # Test angle normalization
        @test get_direction_sector(360.0).name == "N"
        @test get_direction_sector(405.0).name == "NE"  # 45° + 360°
        @test get_direction_sector(-45.0).name == "NW"  # 315° - 360°
        
        # Test center values
        @test get_direction_sector(0.0).center == 0.0
        @test get_direction_sector(45.0).center == 45.0
        @test get_direction_sector(90.0).center == 90.0
    end

    @testset "abs_degree_diff" begin
        # Test normal angle differences
        @test abs_degree_diff(0.0, 10.0) == 10.0
        @test abs_degree_diff(10.0, 0.0) == 10.0
        @test abs_degree_diff(45.0, 90.0) == 45.0
        @test abs_degree_diff(90.0, 45.0) == 45.0
        
        # Test angles crossing 0°/360° boundary
        @test abs_degree_diff(350.0, 10.0) == 20.0
        @test abs_degree_diff(10.0, 350.0) == 20.0
        @test abs_degree_diff(359.0, 1.0) == 2.0
        @test abs_degree_diff(1.0, 359.0) == 2.0
        
        # Test angles > 360° or < 0°
        @test abs_degree_diff(370.0, 10.0) == 0.0  # 370° = 10°
        @test abs_degree_diff(10.0, 370.0) == 0.0
        @test abs_degree_diff(-10.0, 10.0) == 20.0  # -10° = 350°
        @test abs_degree_diff(10.0, -10.0) == 20.0
        @test abs_degree_diff(-350.0, 10.0) == 0.0  # -350° = 10°
        
        # Test identical angles
        @test abs_degree_diff(0.0, 0.0) == 0.0
        @test abs_degree_diff(360.0, 0.0) == 0.0
        @test abs_degree_diff(720.0, 0.0) == 0.0  # 720° = 0°
    end

    @testset "degree_diff" begin
        # Test normal angle differences (within ±180°)
        @test degree_diff(0.0, 10.0) == -10.0  # Counterclockwise is negative
        @test degree_diff(10.0, 0.0) == 10.0   # Clockwise is positive
        @test degree_diff(45.0, 90.0) == -45.0
        @test degree_diff(90.0, 45.0) == 45.0
        
        # Test angles crossing 0°/360° boundary
        @test degree_diff(350.0, 10.0) == -20.0  # Shortest path is CCW
        @test degree_diff(10.0, 350.0) == 20.0   # Shortest path is CW
        @test degree_diff(359.0, 1.0) == -2.0
        @test degree_diff(1.0, 359.0) == 2.0
        
        # Test angles > 360° or < 0°
        @test degree_diff(370.0, 10.0) == 0.0    # 370° = 10°
        @test degree_diff(10.0, 370.0) == 0.0
        @test degree_diff(-10.0, 10.0) == -20.0  # -10° = 350°
        @test degree_diff(10.0, -10.0) == 20.0
        @test degree_diff(-350.0, 10.0) == 0.0  # -350° = 10°
        
        # Test angles at 180° difference
        @test degree_diff(180.0, 0.0) == -180.0
        @test degree_diff(0.0, 180.0) == -180.0
        
        # Test identical angles
        @test degree_diff(0.0, 0.0) == 0.0
        @test degree_diff(360.0, 0.0) == 0.0
        @test degree_diff(720.0, 0.0) == 0.0  # 720° = 0°
    end
end

end # module 
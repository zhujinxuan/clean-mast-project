module TestSector

using Test
using CleanMastProject.Types.Sector: get_direction_sector, DirectionSector

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
end

end # module 
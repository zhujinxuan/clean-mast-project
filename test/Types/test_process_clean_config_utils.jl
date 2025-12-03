using Test
using CleanMastProject.Types.ProcessCleanConfig: load_rules
using CleanMastProject.Types.CleanRules: Rule, RangeCriteria, IcingCriteria, LayerDifferenceCriteria
using CleanMastProject.CleanMastUtils: load_dict
using TOML

@testset "ProcessCleanConfig Utilities" begin
    @testset "load_rules from TOML file" begin
        # Create a temporary rules file
        mktempdir() do tmpdir
            rules_file = joinpath(tmpdir, "test-rules.toml")

            # Write a simple rules file
            rules_config = Dict(
                "rules" => [
                    Dict(
                        "name" => "test_range_rule",
                        "sensorType" => "WindSpeed",
                        "out_of_range" => Dict(
                            "min" => 0.0,
                            "max" => 100.0
                        )
                    ),
                    Dict(
                        "name" => "test_icing_rule",
                        "sensorType" => "WindSpeed",
                        "icing" => Dict(
                            "time_range" => 6,
                            "max_change" => 0.5
                        )
                    )
                ]
            )

            open(rules_file, "w") do io
                TOML.print(io, rules_config)
            end

            # Load rules using load_rules function
            rules = load_rules("test-rules.toml", tmpdir)

            # Verify results
            @test length(rules) == 2
            @test rules[1].name == "test_range_rule"
            @test rules[1].sensorType == "WindSpeed"
            @test rules[1].criteria isa RangeCriteria
            @test rules[2].name == "test_icing_rule"
            @test rules[2].sensorType == "WindSpeed"
            @test rules[2].criteria isa IcingCriteria
        end
    end

    @testset "load_rules from inline Array config" begin
        # Test with inline Array configuration
        rules_config = [
            Dict(
                "name" => "inline_range_rule",
                "sensorType" => "WindSpeed",
                "out_of_range" => Dict(
                    "min" => 0.0,
                    "max" => 50.0
                )
            ),
            Dict(
                "name" => "inline_layer_diff_rule",
                "sensorType" => "WindSpeed",
                "layer_difference" => Dict(
                    "lower_layer_height" => 80.0,
                    "abs_diff" => Dict("min" => nothing, "max" => 10.0),
                    "lower_wind_speed" => Dict("min" => nothing, "max" => nothing)
                )
            )
        ]

        # Load rules from inline config
        rules = load_rules(rules_config, ".")

        # Verify results
        @test length(rules) == 2
        @test rules[1].name == "inline_range_rule"
        @test rules[1].sensorType == "WindSpeed"
        @test rules[1].criteria isa RangeCriteria
        @test rules[2].name == "inline_layer_diff_rule"
        @test rules[2].sensorType == "WindSpeed"
        @test rules[2].criteria isa LayerDifferenceCriteria
    end

    @testset "load_rules with relative path" begin
        # Test that relative paths are resolved correctly
        mktempdir() do tmpdir
            # Create a subdirectory for rules
            rules_dir = joinpath(tmpdir, "configs")
            mkdir(rules_dir)

            rules_file = joinpath(rules_dir, "rules.toml")

            rules_config = Dict(
                "rules" => [
                    Dict(
                        "name" => "relative_path_rule",
                        "sensorType" => "WindSpeed",
                        "out_of_range" => Dict(
                            "min" => 0.0,
                            "max" => 10.0
                        )
                    )
                ]
            )

            open(rules_file, "w") do io
                TOML.print(io, rules_config)
            end

            # Load with relative path from tmpdir
            rules = load_rules("configs/rules.toml", tmpdir)

            @test length(rules) == 1
            @test rules[1].name == "relative_path_rule"
        end
    end

    @testset "load_rules with empty inline config" begin
        # Test with empty rules array
        rules_config = []

        rules = load_rules(rules_config, ".")

        @test isempty(rules)
    end
end

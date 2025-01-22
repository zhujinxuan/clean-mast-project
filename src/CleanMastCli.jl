module CleanMastCli

using Comonicon

"""
project

Project setup and management commands
"""
Comonicon.@cast module Project
    using Comonicon
    using CleanMastProject.Command.QuickStart
    using CleanMastProject.Command.CheckConfig
    using CleanMastProject.Command.CheckSensors
    using CleanMastProject.Command.CleanFiles

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
    check-config

    Validate configuration files.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function check_config(dir::String)
        CheckConfig.execute(dir)
    end

    """
    check-sensors

    List detected sensors and metadata.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function check_sensors(dir::String)
        CheckSensors.execute(dir)
    end

    """
    clean-files

    Archive non-essential files.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function clean_files(dir::String)
        CleanFiles.execute(dir)
    end
end

"""
process

Data processing and reconstruction commands
"""
Comonicon.@cast module Process
    using Comonicon
    using CleanMastProject.Command.CleanData
    using CleanMastProject.Command.TowerShading
    using CleanMastProject.Command.ReconstructSingleMast
    using CleanMastProject.Command.ReconstructMeso
    using CleanMastProject.Command.RepresentativeYearCalibration

    """
    clean

    Clean data using configured rules.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function clean(dir::String)
        CleanData.execute(dir)
    end

    """
    tower-shading

    Apply tower shading detection and correction.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function tower_shading(dir::String)
        TowerShading.execute(dir)
    end

    """
    reconstruct-single

    Reconstruct missing data using single mast data.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function reconstruct_single(dir::String)
        ReconstructSingleMast.execute(dir)
    end

    """
    reconstruct-meso

    Reconstruct missing data using mesoscale data.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function reconstruct_meso(dir::String)
        ReconstructMeso.execute(dir)
    end

    """
    representative-year

    Calibrate data to a representative year.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function representative_year(dir::String)
        RepresentativeYearCalibration.execute(dir)
    end
end

"""
analyze

Analysis and reporting commands
"""
Comonicon.@cast module Analyze
    using Comonicon
    using CleanMastProject.Command.TurbulenceIntensity

    """
    turbulence

    Calculate turbulence intensity metrics.

    # Arguments
    - `dir`: Project directory containing config.yaml
    """
    Comonicon.@cast function turbulence(dir::String)
        TurbulenceIntensity.execute(dir)
    end
end

"""
CleanMast - Wind measurement data cleaning and analysis tool

A command-line tool for processing wind measurement data.
"""
Comonicon.@main

end # module CleanMastCli
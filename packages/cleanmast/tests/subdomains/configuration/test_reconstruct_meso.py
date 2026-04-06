"""Tests for ReconstructMeso configuration models."""

from datetime import datetime

from cleanmast.subdomains.configuration import (
    MesoSource,
    ReconstructMesoConfiguration,
    ReconstructMesoMast,
    ReconstructMesoModels,
    ReconstructMesoModelSpec,
)
from cleanmast.subdomains.dataingestion.value_objects.time_range import TimeRange
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class TestReconstructMesoModelSpec:
    """Tests for ReconstructMesoModelSpec model."""

    def test_create_model_spec(self):
        """Test creating a model specification."""
        spec = ReconstructMesoModelSpec(
            method="1-sector",
            meso_name="era5-002824",
            model_file="./meso-models/M01/era5/windspeed/1-sector.jld2",
        )

        assert spec.method == "1-sector"
        assert spec.meso_name == "era5-002824"
        assert spec.model_file == "./meso-models/M01/era5/windspeed/1-sector.jld2"

    def test_create_from_dict(self):
        """Test creating from dict (like TOML input)."""
        data = {
            "method": "constant-offset",
            "meso_name": "freemeso-M01",
            "model_file": "./models/winddirection.jld2",
        }

        spec = ReconstructMesoModelSpec(**data)

        assert spec.method == "constant-offset"
        assert spec.meso_name == "freemeso-M01"


class TestReconstructMesoModels:
    """Tests for ReconstructMesoModels model."""

    def test_create_models(self):
        """Test creating windspeed and winddirection model specs."""
        models = ReconstructMesoModels(
            windspeed=ReconstructMesoModelSpec(
                method="1-sector",
                meso_name="era5-M01",
                model_file="./ws-model.jld2",
            ),
            winddirection=ReconstructMesoModelSpec(
                method="constant-offset",
                meso_name="era5-M01",
                model_file="./wd-model.jld2",
            ),
        )

        assert models.windspeed.method == "1-sector"
        assert models.winddirection.method == "constant-offset"


class TestMesoSource:
    """Tests for MesoSource model (TrainMesoSource in Julia)."""

    def test_create_meso_source(self):
        """Test creating a meso source."""
        source = MesoSource(
            name="era5-002824",
            input=TimeSeriesSource(
                data="./raw/era5-002824.csv",
                sensors="./raw/era5-002824.sensors.toml",
            ),
        )

        assert source.name == "era5-002824"
        assert source.input.data == "./raw/era5-002824.csv"


class TestReconstructMesoMast:
    """Tests for ReconstructMesoMast model."""

    def test_create_mast_config(self):
        """Test creating a full mast configuration."""
        mast = ReconstructMesoMast(
            name="pn-002824",
            input=TimeSeriesSource(
                data="./reconstruct-single/pn-002824.csv",
                sensors="./reconstruct-single/pn-002824.sensors.yaml",
            ),
            output=TimeSeriesSource(
                data="./reconstruct-meso/pn-002824.csv",
                sensors="./reconstruct-meso/pn-002824.sensors.yaml",
            ),
            time_range=TimeRange(
                min=datetime(2024, 1, 1),
                max=datetime(2024, 12, 31, 23, 59, 59),
            ),
            models=ReconstructMesoModels(
                windspeed=ReconstructMesoModelSpec(
                    method="1-sector",
                    meso_name="era5-002824",
                    model_file="./meso-models/ws.jld2",
                ),
                winddirection=ReconstructMesoModelSpec(
                    method="constant-offset",
                    meso_name="era5-002824",
                    model_file="./meso-models/wd.jld2",
                ),
            ),
        )

        assert mast.name == "pn-002824"
        assert mast.input.data == "./reconstruct-single/pn-002824.csv"
        assert mast.output.data == "./reconstruct-meso/pn-002824.csv"
        assert mast.time_range.min.year == 2024
        assert mast.models.windspeed.method == "1-sector"


class TestReconstructMesoConfiguration:
    """Tests for ReconstructMesoConfiguration model."""

    def test_create_configuration(self):
        """Test creating a full configuration."""
        config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./in/M01.csv", sensors="./in/M01.sensors.yaml"),
                    output=TimeSeriesSource(data="./out/M01.csv", sensors="./out/M01.sensors.yaml"),
                    time_range=TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31)),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(
                            method="1-sector", meso_name="era5", model_file="./ws.jld2"
                        ),
                        winddirection=ReconstructMesoModelSpec(
                            method="constant-offset", meso_name="era5", model_file="./wd.jld2"
                        ),
                    ),
                )
            ],
            mesos=[
                MesoSource(
                    name="era5",
                    input=TimeSeriesSource(data="./raw/era5.csv", sensors="./raw/era5.sensors.toml"),
                )
            ],
        )

        assert len(config.masts) == 1
        assert len(config.mesos) == 1
        assert config.masts[0].name == "M01"
        assert config.mesos[0].name == "era5"

    def test_create_from_nested_dict(self):
        """Test creating configuration from nested dict (like TOML parsing)."""
        # Build proper model instances for pyright compatibility
        mast = ReconstructMesoMast(
            name="pn-002824",
            input=TimeSeriesSource(data="./in/data.csv", sensors="./in/sensors.yaml"),
            output=TimeSeriesSource(data="./out/data.csv", sensors="./out/sensors.yaml"),
            time_range=TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31)),
            models=ReconstructMesoModels(
                windspeed=ReconstructMesoModelSpec(
                    method="1-sector",
                    meso_name="era5",
                    model_file="./ws.jld2",
                ),
                winddirection=ReconstructMesoModelSpec(
                    method="constant-offset",
                    meso_name="era5",
                    model_file="./wd.jld2",
                ),
            ),
        )
        meso = MesoSource(
            name="era5",
            input=TimeSeriesSource(data="./raw/era5.csv", sensors="./raw/era5.sensors.toml"),
        )

        config = ReconstructMesoConfiguration(masts=[mast], mesos=[meso])

        assert config.masts[0].name == "pn-002824"
        assert config.masts[0].models.windspeed.method == "1-sector"
        assert config.mesos[0].name == "era5"

    def test_get_mast_output_paths(self):
        """Test accessing mast output paths for extrapolation."""
        config = ReconstructMesoConfiguration(
            masts=[
                ReconstructMesoMast(
                    name="M01",
                    input=TimeSeriesSource(data="./in/M01.csv", sensors="./in/M01.sensors.yaml"),
                    output=TimeSeriesSource(
                        data="./reconstruct-meso/M01.csv",
                        sensors="./reconstruct-meso/M01.sensors.yaml",
                    ),
                    time_range=TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31)),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(
                            method="1-sector", meso_name="era5", model_file="./ws.jld2"
                        ),
                        winddirection=ReconstructMesoModelSpec(
                            method="constant-offset", meso_name="era5", model_file="./wd.jld2"
                        ),
                    ),
                ),
                ReconstructMesoMast(
                    name="M02",
                    input=TimeSeriesSource(data="./in/M02.csv", sensors="./in/M02.sensors.yaml"),
                    output=TimeSeriesSource(
                        data="./reconstruct-meso/M02.csv",
                        sensors="./reconstruct-meso/M02.sensors.yaml",
                    ),
                    time_range=TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31)),
                    models=ReconstructMesoModels(
                        windspeed=ReconstructMesoModelSpec(
                            method="1-sector", meso_name="era5", model_file="./ws.jld2"
                        ),
                        winddirection=ReconstructMesoModelSpec(
                            method="constant-offset", meso_name="era5", model_file="./wd.jld2"
                        ),
                    ),
                ),
            ],
            mesos=[],
        )

        # This is how recommend extrapolate-wind will access output paths
        output_paths = [(m.name, m.output) for m in config.masts]

        assert len(output_paths) == 2
        assert output_paths[0][0] == "M01"
        assert output_paths[0][1].data == "./reconstruct-meso/M01.csv"
        assert output_paths[1][0] == "M02"

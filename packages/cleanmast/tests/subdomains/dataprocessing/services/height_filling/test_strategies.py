"""Tests for fill_heights strategy classes."""


from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.subdomains.configuration import (
    WindDirectionHeightConfig,
    WindSpeedHeightConfig,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.helpers import (
    create_fill_target_sensor,
    get_existing_sensors,
    get_top_sensors,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.strategies.wd_extrapolate_top3 import (
    WDExtrapolateTop3Strategy,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.strategies.wd_interpolate_inter import (
    WDInterpolateInterStrategy,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.strategies.ws_extrapolate_top3 import (
    WSExtrapolateTop3Strategy,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.strategies.ws_interpolate_inter import (
    WSInterpolateInterStrategy,
)


class TestWSExtrapolateTop3Strategy:
    """Tests for WSExtrapolateTop3Strategy."""

    def test_ws_extrapolate_top3_builds_config(self, sample_timeseries: TimeSeriesData):
        """Test that strategy builds valid extrapolation config."""
        strategy = WSExtrapolateTop3Strategy()
        target = create_fill_target_sensor(
            sample_timeseries, 120.0, "WindSpeed", "extrapolated"
        )
        references = get_top_sensors(sample_timeseries, "WindSpeed", n=3)
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )

        assert config is not None
        assert isinstance(config, WindSpeedHeightConfig)
        assert config.target_column == "WS_120m_fill:extrapolated"
        assert config.shear == 0.14
        assert len(config.references) == 1
        assert config.references[0].sensor.height == 100.0  # Highest existing
        assert config.references[0].sensor.column_name == "WS_100m_avg"

    def test_ws_extrapolate_top3_returns_none_if_not_applicable(self, sample_timeseries: TimeSeriesData):
        """Test that strategy returns None when target is not above existing."""
        strategy = WSExtrapolateTop3Strategy()
        references = get_top_sensors(sample_timeseries, "WindSpeed", n=3)

        # Target at existing height
        target = create_fill_target_sensor(
            sample_timeseries, 100.0, "WindSpeed", "extrapolated"
        )
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )
        assert config is None

        # Target below existing
        target = create_fill_target_sensor(
            sample_timeseries, 80.0, "WindSpeed", "extrapolated"
        )
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )
        assert config is None

    def test_ws_extrapolate_top3_uses_pre_fitted_shear(self, sample_timeseries: TimeSeriesData):
        """Test that strategy uses the pre-fitted shear value."""
        strategy = WSExtrapolateTop3Strategy()
        custom_shear = 0.25
        target = create_fill_target_sensor(
            sample_timeseries, 120.0, "WindSpeed", "extrapolated"
        )
        references = get_top_sensors(sample_timeseries, "WindSpeed", n=3)

        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=custom_shear,
        )

        assert config is not None
        assert config.shear == custom_shear


class TestWSInterpolateInterStrategy:
    """Tests for WSInterpolateInterStrategy."""

    def test_ws_interpolate_inter_builds_config(self, sample_timeseries: TimeSeriesData):
        """Test that strategy builds valid interpolation config."""
        strategy = WSInterpolateInterStrategy()
        target = create_fill_target_sensor(
            sample_timeseries, 65.0, "WindSpeed", "interpolated"
        )
        existing = get_existing_sensors(sample_timeseries.sensors, "WindSpeed")
        references = [s for s in existing if s.height in (50.0, 80.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )

        assert config is not None
        assert isinstance(config, WindSpeedHeightConfig)
        assert config.target_column == "WS_65m_fill:interpolated"
        assert len(config.references) == 2
        assert config.references[0].sensor.column_name == "WS_50m_avg"
        assert config.references[1].sensor.column_name == "WS_80m_avg"

    def test_ws_interpolate_inter_returns_none_if_not_applicable(self, sample_timeseries: TimeSeriesData):
        """Test that strategy returns None when target is outside range."""
        strategy = WSInterpolateInterStrategy()
        existing = get_existing_sensors(sample_timeseries.sensors, "WindSpeed")

        # Target above max
        target = create_fill_target_sensor(
            sample_timeseries, 120.0, "WindSpeed", "interpolated"
        )
        references = [s for s in existing if s.height in (80.0, 100.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )
        assert config is None

        # Target below min
        target = create_fill_target_sensor(
            sample_timeseries, 30.0, "WindSpeed", "interpolated"
        )
        references = [s for s in existing if s.height in (50.0, 80.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )
        assert config is None

    def test_ws_interpolate_inter_calculates_weights(self, sample_timeseries: TimeSeriesData):
        """Test that strategy calculates proper interpolation weights."""
        strategy = WSInterpolateInterStrategy()
        target = create_fill_target_sensor(
            sample_timeseries, 65.0, "WindSpeed", "interpolated"
        )
        existing = get_existing_sensors(sample_timeseries.sensors, "WindSpeed")
        references = [s for s in existing if s.height in (50.0, 80.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            shear=0.14,
        )

        assert config is not None
        # 65m is 15m from 50m and 15m from 80m
        # So weights should be approximately equal
        total_weight = config.references[0].weight + config.references[1].weight
        assert abs(total_weight - 1.0) < 0.001


class TestWDExtrapolateTop3Strategy:
    """Tests for WDExtrapolateTop3Strategy."""

    def test_wd_extrapolate_top3_builds_config(self, sample_timeseries: TimeSeriesData):
        """Test that strategy builds valid extrapolation config."""
        strategy = WDExtrapolateTop3Strategy()
        target = create_fill_target_sensor(
            sample_timeseries, 120.0, "WindDirection", "extrapolated"
        )
        references = get_top_sensors(sample_timeseries, "WindDirection", n=3)
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )

        assert config is not None
        assert isinstance(config, WindDirectionHeightConfig)
        assert config.target_column == "WD_120m_fill:extrapolated"
        assert config.deg_diff_per_m == 0.05
        assert len(config.references) == 1
        assert config.references[0].sensor.height == 100.0  # Highest existing
        assert config.references[0].sensor.column_name == "WD_100m_avg"

    def test_wd_extrapolate_top3_returns_none_if_not_applicable(self, sample_timeseries: TimeSeriesData):
        """Test that strategy returns None when target is not above existing."""
        strategy = WDExtrapolateTop3Strategy()
        references = get_top_sensors(sample_timeseries, "WindDirection", n=3)

        # Target at existing height
        target = create_fill_target_sensor(
            sample_timeseries, 100.0, "WindDirection", "extrapolated"
        )
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )
        assert config is None

        # Target below existing
        target = create_fill_target_sensor(
            sample_timeseries, 80.0, "WindDirection", "extrapolated"
        )
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )
        assert config is None

    def test_wd_extrapolate_top3_uses_pre_fitted_deg_diff(self, sample_timeseries: TimeSeriesData):
        """Test that strategy uses the pre-fitted deg_diff value."""
        strategy = WDExtrapolateTop3Strategy()
        custom_deg_diff = 0.1
        target = create_fill_target_sensor(
            sample_timeseries, 120.0, "WindDirection", "extrapolated"
        )
        references = get_top_sensors(sample_timeseries, "WindDirection", n=3)

        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=custom_deg_diff,
        )

        assert config is not None
        assert config.deg_diff_per_m == custom_deg_diff


class TestWDInterpolateInterStrategy:
    """Tests for WDInterpolateInterStrategy."""

    def test_wd_interpolate_inter_builds_config(self, sample_timeseries: TimeSeriesData):
        """Test that strategy builds valid interpolation config."""
        strategy = WDInterpolateInterStrategy()
        target = create_fill_target_sensor(
            sample_timeseries, 65.0, "WindDirection", "interpolated"
        )
        existing = get_existing_sensors(sample_timeseries.sensors, "WindDirection")
        references = [s for s in existing if s.height in (50.0, 80.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )

        assert config is not None
        assert isinstance(config, WindDirectionHeightConfig)
        assert config.target_column == "WD_65m_fill:interpolated"
        assert len(config.references) == 2
        assert config.references[0].sensor.column_name == "WD_50m_avg"
        assert config.references[1].sensor.column_name == "WD_80m_avg"

    def test_wd_interpolate_inter_returns_none_if_not_applicable(self, sample_timeseries: TimeSeriesData):
        """Test that strategy returns None when target is outside range."""
        strategy = WDInterpolateInterStrategy()
        existing = get_existing_sensors(sample_timeseries.sensors, "WindDirection")

        # Target above max
        target = create_fill_target_sensor(
            sample_timeseries, 120.0, "WindDirection", "interpolated"
        )
        references = [s for s in existing if s.height in (80.0, 100.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )
        assert config is None

        # Target below min
        target = create_fill_target_sensor(
            sample_timeseries, 30.0, "WindDirection", "interpolated"
        )
        references = [s for s in existing if s.height in (50.0, 80.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )
        assert config is None

    def test_wd_interpolate_inter_calculates_weights(self, sample_timeseries: TimeSeriesData):
        """Test that strategy calculates proper interpolation weights."""
        strategy = WDInterpolateInterStrategy()
        target = create_fill_target_sensor(
            sample_timeseries, 65.0, "WindDirection", "interpolated"
        )
        existing = get_existing_sensors(sample_timeseries.sensors, "WindDirection")
        references = [s for s in existing if s.height in (50.0, 80.0)]
        config = strategy.build_config(
            timeseries=sample_timeseries,
            target=target,
            references=references,
            deg_diff_per_m=0.05,
        )

        assert config is not None
        # Weights should sum to 1.0
        total_weight = config.references[0].weight + config.references[1].weight
        assert abs(total_weight - 1.0) < 0.001

    def test_strategy_names(self):
        """Test that all strategies have correct names."""
        assert WSExtrapolateTop3Strategy.name == "ws-extrapolate-top3"
        assert WSInterpolateInterStrategy.name == "ws-interpolate-inter"
        assert WDExtrapolateTop3Strategy.name == "wd-extrapolate-top3"
        assert WDInterpolateInterStrategy.name == "wd-interpolate-inter"

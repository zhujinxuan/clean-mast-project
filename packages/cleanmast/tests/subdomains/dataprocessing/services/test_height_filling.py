"""Tests for height filling DDD services."""

import polars as pl
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataprocessing.services.height_filling import (
    build_sensor_column_map,
    create_fill_target_sensor,
    find_neighbor_sensors,
    get_existing_sensors,
    get_top_sensors,
)


class TestHeightFillingServices:
    """Tests for height filling services."""

    def test_get_existing_sensors_filters_by_type(self):
        """Test that get_existing_sensors filters by sensor type."""
        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        ws_sensors = get_existing_sensors(sensors, "WindSpeed")
        assert len(ws_sensors) == 1
        assert ws_sensors[0].sensor_type == "WindSpeed"

    def test_get_top_sensors_returns_highest(self):
        """Test that get_top_sensors returns highest sensors."""
        sensors = [
            SensorColumn(
                column_name="WS_50m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=50.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "WS_50m_avg": [5.0, 6.0, 7.0],
            "WS_80m_avg": [7.0, 8.0, 9.0],
            "WS_100m_avg": [9.0, 10.0, 11.0],
        })
        timeseries = TimeSeriesData(df=df, sensors=sensors)

        top = get_top_sensors(timeseries, "WindSpeed", n=2)
        assert len(top) == 2
        assert top[0].height == 100.0
        assert top[1].height == 80.0

    def test_find_neighbor_sensors_finds_correct_pair(self):
        """Test finding neighbor sensors."""
        sensors = [
            SensorColumn(
                column_name="WS_50m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=50.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        lower, higher = find_neighbor_sensors(75.0, sensors)
        assert lower.height == 50.0
        assert higher.height == 80.0

    def test_create_fill_target_sensor(self):
        """Test creating fill target sensor."""
        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        df = pl.DataFrame({"timestamp": [1], "WS_80m_avg": [8.0]})
        timeseries = TimeSeriesData(df=df, sensors=sensors)

        target = create_fill_target_sensor(
            timeseries, 120.0, "WindSpeed", "extrapolated"
        )

        assert target.column_name == "WS_120m_fill:extrapolated"
        assert target.height == 120.0
        assert target.sensor_type == "WindSpeed"
        assert target.unit == "m/s"

    def test_build_sensor_column_map(self):
        """Test building sensor column map."""
        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        df = pl.DataFrame({"timestamp": [1], "WS_80m_avg": [8.0]})
        timeseries = TimeSeriesData(df=df, sensors=sensors)

        col_map = build_sensor_column_map(timeseries)
        assert "WS_80m_avg" in col_map
        assert col_map["WS_80m_avg"].height == 80.0

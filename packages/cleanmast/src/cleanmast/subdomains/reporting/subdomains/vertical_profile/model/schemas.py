import dataframely as dy


class VerticalProfileSchema(dy.Schema):
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    wind_speed_mean = dy.Float64(nullable=False)
    wind_speed_std = dy.Float64(nullable=False)
    alpha = dy.Float64(nullable=True)
    r_squared = dy.Float64(nullable=True)


class WindShearSchema(dy.Schema):
    from_height = dy.Float64(nullable=False)
    to_height = dy.Float64(nullable=False)
    alpha_mean = dy.Float64(nullable=False)
    alpha_std = dy.Float64(nullable=False)
    alpha_min = dy.Float64(nullable=False)
    alpha_max = dy.Float64(nullable=False)


__all__ = ["VerticalProfileSchema", "WindShearSchema"]

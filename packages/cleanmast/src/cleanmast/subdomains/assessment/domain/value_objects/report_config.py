"""报告配置模型。

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Validation ✓
Description: 报告生成配置的数据模型，支持从 YAML 文件加载
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ReportSubsectionConfig:
    """报告子章节配置。

    控制报告中各个分析章节的启用状态。

    Attributes:
        windrose: 是否启用风玫瑰图章节
        windtemporal: 是否启用风速时间序列章节
        weibull: 是否启用威布尔分布章节
        windfrequency: 是否启用风频分析章节
        turbulence: 是否启用湍流强度章节
        verticalprofile: 是否启用垂直风廓线章节
    """

    windrose: bool = True
    windtemporal: bool = True
    weibull: bool = True
    windfrequency: bool = True
    turbulence: bool = True
    verticalprofile: bool = True


@dataclass
class ReportConfig:
    """报告生成配置。

    定义单测风塔分析报告的所有配置参数，
    包括输入数据、子章节开关、空气密度设置和输出选项。

    Attributes:
        mast_name: 测风塔名称
        input_data: 输入数据文件路径（Parquet 格式）
        subsections: 子章节配置对象
        air_density: 空气密度配置字典，包含 method 和 value 字段
        output: 输出配置字典，包含 directory 和 format 字段
    """

    mast_name: str
    input_data: Path
    subsections: ReportSubsectionConfig = field(
        default_factory=ReportSubsectionConfig
    )
    air_density: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后验证配置值。

        验证输出格式必须为 "typst"。

        Raises:
            ValueError: 当输出格式不是 "typst" 时
        """
        output_format = self.output.get("format", "")
        if output_format and output_format != "typst":
            raise ValueError(
                f"输出格式必须为 'typst'，但得到: {output_format}"
            )

        if isinstance(self.input_data, str):
            object.__setattr__(self, "input_data", Path(self.input_data))

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "ReportConfig":
        """从 YAML 文件加载报告配置。

        读取 YAML 配置文件并转换为 ReportConfig 对象。
        YAML 格式支持嵌套的子章节配置。

        Args:
            yaml_path: YAML 配置文件路径

        Returns:
            ReportConfig: 解析后的报告配置对象

        Raises:
            FileNotFoundError: 当 YAML 文件不存在时
            ValueError: 当 YAML 格式无效或缺少必需字段时

        Example:
            >>> config = ReportConfig.from_yaml("./config/report.yaml")
            >>> print(config.mast_name)
            'M01'
        """
        yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"配置文件未找到: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("YAML 文件内容必须是字典类型")

        mast_name = data.get("mast_name")
        if not mast_name:
            raise ValueError("YAML 配置缺少必需字段: mast_name")

        input_data = data.get("input_data")
        if not input_data:
            raise ValueError("YAML 配置缺少必需字段: input_data")

        subsections_data = data.get("subsections", {})
        subsections = cls._parse_subsections(subsections_data)

        air_density = data.get("air_density", {})

        output = data.get("output", {})

        return cls(
            mast_name=mast_name,
            input_data=Path(input_data),
            subsections=subsections,
            air_density=air_density,
            output=output,
        )

    @staticmethod
    def _parse_subsections(
        subsections_data: dict[str, Any]
    ) -> ReportSubsectionConfig:
        """解析子章节配置数据。

        从 YAML 中的子章节配置字典创建 ReportSubsectionConfig 对象。
        支持两种格式：
        1. 简写格式: {subsection_name: true/false}
        2. 完整格式: {subsection_name: {enabled: true, ...}}

        Args:
            subsections_data: YAML 中的子章节配置字典

        Returns:
            ReportSubsectionConfig: 解析后的子章节配置
        """
        kwargs: dict[str, bool] = {}

        field_mapping = {
            "windrose": "windrose",
            "windtemporal": "windtemporal",
            "weibull": "weibull",
            "windfrequency": "windfrequency",
            "turbulence": "turbulence",
            "verticalprofile": "verticalprofile",
        }

        for yaml_key, attr_name in field_mapping.items():
            if yaml_key in subsections_data:
                value = subsections_data[yaml_key]
                if isinstance(value, bool):
                    kwargs[attr_name] = value
                elif isinstance(value, dict):
                    kwargs[attr_name] = value.get("enabled", True)
                else:
                    kwargs[attr_name] = bool(value)

        return ReportSubsectionConfig(**kwargs)

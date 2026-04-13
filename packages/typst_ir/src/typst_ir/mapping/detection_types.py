"""Type aliases for IR node inputs used by the detection module."""

from typing import Any, TypedDict, Union


class DetectionParagraph(TypedDict):
    text: str
    details: Any


class DetectionHeading(TypedDict):
    text: str
    level: int
    details: Any


class DetectionTable(TypedDict):
    data: list[list[str]]
    headers: list[str]
    caption: str | None
    details: Any


class DetectionFigure(TypedDict):
    content: str
    caption: str
    kind: str
    details: Any


class DetectionEquation(TypedDict):
    latex: str
    display: bool
    details: Any


DetectionNode = Union[
    DetectionParagraph,
    DetectionHeading,
    DetectionTable,
    DetectionFigure,
    DetectionEquation,
]

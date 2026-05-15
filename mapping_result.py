from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class ColumnMapping:
    part_col: str | None = None
    qty_col: str | None = None
    station_col: str | None = None
    location_col: str | None = None
    side_col: str | None = None
    position_col: str | None = None
    variant_col: str | None = None
    description_col: str | None = None
    alternative_part_col: str | None = None
    confidence_scores: dict = field(default_factory=dict)
    mapping_method: str = "unknown"
    warnings: list = field(default_factory=list)

    def has_station(self) -> bool:
        return self.station_col is not None or self.location_col is not None

    def has_context(self) -> bool:
        return any([self.station_col, self.side_col, self.position_col, self.variant_col])

    def get_station_field(self) -> str | None:
        return self.station_col or self.location_col

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from curation_validation.core.loader import DataSource


@dataclass
class ValidatorContext:
    csv_file: Optional[Path]
    json_dir: Optional[Path]
    output_dir: Path
    data_source: Optional[DataSource]
    geonames_user: Optional[str]


class BaseValidator(ABC):
    name: str = ""
    supported_formats: set[str] = set()
    output_filename: str = ""
    output_fields: list[str] = []
    requires_data_source: bool = False
    requires_geonames: bool = False

    @abstractmethod
    def run(self, ctx: ValidatorContext) -> list[dict]:
        pass

    def can_run(self, ctx: ValidatorContext) -> tuple[bool, str]:
        if self.requires_geonames and ctx.geonames_user is None:
            return False, f"{self.name} requires --geonames-user"
        if self.requires_data_source and ctx.data_source is None:
            return False, f"{self.name} requires --data-dump"
        return True, ""

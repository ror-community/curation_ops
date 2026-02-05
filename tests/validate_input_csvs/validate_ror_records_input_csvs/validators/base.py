from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from validate_ror_records_input_csvs.core.loader import DataSource


@dataclass
class ValidatorContext:
    input_file: Path
    output_dir: Path
    data_source: Optional[DataSource]
    geonames_user: Optional[str]


class BaseValidator(ABC):
    name: str = ""
    output_filename: str = ""
    output_fields: list[str] = []
    requires_data_source: bool = False
    requires_geonames: bool = False
    new_records_only: bool = False

    @abstractmethod
    def run(self, ctx: ValidatorContext) -> list[dict]:
        pass

    def can_run(self, ctx: ValidatorContext) -> tuple[bool, str]:
        if self.requires_geonames and ctx.geonames_user is None:
            return False, f"{self.name} requires --geonames-user"
        return True, ""

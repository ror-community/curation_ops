"""Validator registration and exports."""

from validate_ror_records_input_csvs.validators.validate_fields import ValidateFieldsValidator
from validate_ror_records_input_csvs.validators.duplicate_external_ids import DuplicateExternalIdsValidator
from validate_ror_records_input_csvs.validators.duplicate_urls import DuplicateUrlsValidator
from validate_ror_records_input_csvs.validators.address_validation import AddressValidationValidator
from validate_ror_records_input_csvs.validators.in_release_duplicates import InReleaseDuplicatesValidator


def register_all_validators():
    """Called after runner module is loaded to avoid circular imports."""
    from validate_ror_records_input_csvs.runner import register_validator

    register_validator(ValidateFieldsValidator())
    register_validator(DuplicateExternalIdsValidator())
    register_validator(DuplicateUrlsValidator())
    register_validator(AddressValidationValidator())
    register_validator(InReleaseDuplicatesValidator())


__all__ = [
    "ValidateFieldsValidator",
    "DuplicateExternalIdsValidator",
    "DuplicateUrlsValidator",
    "AddressValidationValidator",
    "InReleaseDuplicatesValidator",
    "register_all_validators",
]

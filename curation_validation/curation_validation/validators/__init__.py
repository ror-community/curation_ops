from curation_validation.validators.validate_fields import ValidateFieldsValidator
from curation_validation.validators.duplicate_external_ids import DuplicateExternalIdsValidator
from curation_validation.validators.duplicate_urls import DuplicateUrlsValidator
from curation_validation.validators.address_validation import AddressValidationValidator
from curation_validation.validators.in_release_duplicates import InReleaseDuplicatesValidator
from curation_validation.validators.production_duplicates import ProductionDuplicatesValidator
from curation_validation.validators.duplicate_values import DuplicateValuesValidator
from curation_validation.validators.unprintable_chars import UnprintableCharsValidator
from curation_validation.validators.leading_trailing import LeadingTrailingValidator
from curation_validation.validators.new_record_integrity import NewRecordIntegrityValidator
from curation_validation.validators.update_record_integrity import UpdateRecordIntegrityValidator
from curation_validation.validators.input_file_structure import InputFileStructureValidator


def register_all_validators():
    from curation_validation.runner import register_validator

    register_validator(InputFileStructureValidator())
    register_validator(ValidateFieldsValidator())
    register_validator(DuplicateExternalIdsValidator())
    register_validator(DuplicateUrlsValidator())
    register_validator(AddressValidationValidator())
    register_validator(InReleaseDuplicatesValidator())
    register_validator(ProductionDuplicatesValidator())
    register_validator(DuplicateValuesValidator())
    register_validator(UnprintableCharsValidator())
    register_validator(LeadingTrailingValidator())
    register_validator(NewRecordIntegrityValidator())
    register_validator(UpdateRecordIntegrityValidator())


__all__ = [
    "InputFileStructureValidator",
    "ValidateFieldsValidator",
    "DuplicateExternalIdsValidator",
    "DuplicateUrlsValidator",
    "AddressValidationValidator",
    "InReleaseDuplicatesValidator",
    "ProductionDuplicatesValidator",
    "DuplicateValuesValidator",
    "UnprintableCharsValidator",
    "LeadingTrailingValidator",
    "NewRecordIntegrityValidator",
    "UpdateRecordIntegrityValidator",
    "register_all_validators",
]

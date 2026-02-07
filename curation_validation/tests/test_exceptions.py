from curation_validation.core.exceptions import (
    RecordValidationError,
    DataLoadError,
    ConfigurationError,
)


class TestExceptionHierarchy:
    def test_data_load_error_is_record_validation_error(self):
        assert issubclass(DataLoadError, RecordValidationError)

    def test_configuration_error_is_record_validation_error(self):
        assert issubclass(ConfigurationError, RecordValidationError)

    def test_record_validation_error_is_exception(self):
        assert issubclass(RecordValidationError, Exception)

    def test_data_load_error_message(self):
        err = DataLoadError("file not found")
        assert str(err) == "file not found"

    def test_configuration_error_message(self):
        err = ConfigurationError("missing --csv")
        assert str(err) == "missing --csv"

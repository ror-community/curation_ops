class RecordValidationError(Exception):
    pass


class DataLoadError(RecordValidationError):
    pass


class ConfigurationError(RecordValidationError):
    pass

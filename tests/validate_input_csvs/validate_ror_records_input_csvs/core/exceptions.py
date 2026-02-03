"""Custom exceptions for validate-ror-records-input-csvs."""


class CsvTestsError(Exception):
    pass


class DataLoadError(CsvTestsError):
    pass


class ValidationError(CsvTestsError):
    pass

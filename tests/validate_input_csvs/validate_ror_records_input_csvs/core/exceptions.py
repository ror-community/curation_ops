class CsvTestsError(Exception):
    pass


class DataLoadError(CsvTestsError):
    pass


class ValidationError(CsvTestsError):
    pass

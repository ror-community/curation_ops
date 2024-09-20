import csv

def read_csv(file_path):
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return list(reader)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error: File not found - {e}")
    except IOError as e:
        raise IOError(f"Error: IO Error - {e}")

def write_report(report_data, file_path):
    try:
        with open(file_path, mode='w', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['html_url', 'ror_id', 'error_warning'])
            for data in report_data:
                if isinstance(data, dict):
                    for message in data['messages']:
                        writer.writerow([data['html_url'], data['ror_id'], message])
    except IOError as e:
        raise IOError(f"Error: IO Error while writing the file - {e}")

import argparse
import copy
import json
import os
import logging
from zipfile import ZipFile, ZIP_DEFLATED
ERROR_LOG = "errors.log"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')


def extract_dump(dump_zip_path, output_path):
    dump_unzipped = ''
    converted_records = []
    with ZipFile(dump_zip_path, "r") as zf:
        json_files_count = sum('.json' in s for s in zf.namelist())
        if json_files_count >= 1:
            for name in zf.namelist():
                if 'schema_v2.json' in name:
                    dump_unzipped = zf.extract(name, output_path)
                    return dump_unzipped
        else:
            print("Dump does not contain any json files. Something is wrong.")
    return None

def split_dump(dump_unzipped, output_path, chunk_size):
    saved_files = []
    #try:
    path, dump_filename = os.path.split(dump_unzipped)
    f = open(dump_unzipped, 'r')
    all_records = json.load(f)
    print(str(len(all_records)) + f" records in dump {dump_unzipped}")
    split_records = [all_records[i:i + chunk_size] for i in range(0, len(all_records), chunk_size)]
    print(f"Dump split into {str(len(split_records))} chunks")
    i = 1
    for record_chunk in split_records:
        print(f"Saving chunk {i}")
        chunk_filename = dump_filename.strip(".json") + f"_chunk{i}.json"
        with open(os.path.join(output_path, chunk_filename), "w") as writer:
            writer.write(
                json.dumps(record_chunk, ensure_ascii=False, indent=4, separators=(',', ': '))
            )
        saved_files.append(chunk_filename)
        i += 1
    return saved_files
    #except:
    #    logging.error(f"Error creating v{output_schema_version} dump file: {e}")


def main():
    parser = argparse.ArgumentParser(description="Script to split data dump file into multiple files of specified length")
    parser.add_argument('-o', '--outputpath', type=str, required=True, help="Full path to location where output files should be saved")
    parser.add_argument('-f', '--dumpfile', type=str, required=True, help="Full path to dump file")
    parser.add_argument('-c', '--chunksize', type=int, default=5000, help="Maximum number of record each file should contain")
    args = parser.parse_args()

    if os.path.exists(args.dumpfile):
        #try:
        print(f"Extracting dump {args.dumpfile}")
        dump_unzipped = extract_dump(args.dumpfile, args.outputpath)
        print(f"Splitting unzipped dump {dump_unzipped}")
        saved_files = split_dump(dump_unzipped, args.outputpath, args.chunksize)
        print(f"Files created:")
        print(saved_files)
        #except Exception as e:
        #    logging.error("Error creating new dump: {e}")
    else:
        print(f"File {args.dumpfile} does not exist. Cannot process files.")


    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()


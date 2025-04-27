import os
import re
import gzip
from warcio.archiveiterator import ArchiveIterator
from warcio.warcwriter import WARCWriter

input_dir = "output/20250426220043"
output_dir = "warc"

records_per_file = 1000

record_counter = 0
file_counter = 1
current_writer = None
current_outfile = None


def start_new_output():
    global current_writer, current_outfile, file_counter
    if current_outfile:
        current_outfile.close()
    outfile_path = os.path.join(output_dir, f"output_{file_counter}.warc.gz")
    current_outfile = gzip.open(outfile_path, "wb")
    current_writer = WARCWriter(current_outfile, gzip=True)
    file_counter += 1


start_new_output()


def sort_key(filename):
    match = re.search(r"output-(\d+)\.warc\.gz", filename)
    return int(match.group(1)) if match else -1


input_files = sorted(
    [f for f in os.listdir(input_dir) if f.endswith(".warc.gz")],
    key=sort_key,
)

for input_file in input_files:
    input_path = os.path.join(input_dir, input_file)
    print(f"Processing file: {input_file}")
    with gzip.open(input_path, "rb") as stream:
        for record in ArchiveIterator(stream):
            if record_counter >= records_per_file:
                print(f"Reached {records_per_file} records, starting new output file.")
                start_new_output()
                record_counter = 0
            current_writer.write_record(record)
            record_counter += 1
            if record_counter % 100 == 0:
                print(f"Written {record_counter} records to current file.")

if current_outfile:
    current_outfile.close()
    current_writer = None
    current_outfile = None

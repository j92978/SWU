import csv


def merge_csv_files(input_files, output_file):
    """
    Merge multiple CSV files into one, keeping only the header from the first file.

    Args:
        input_files (list): List of CSV file paths to merge.
        output_file (str): Path of the merged CSV file.
    """
    with open(output_file, "w", newline="", encoding="utf-8") as fout:
        writer = None

        for i, file in enumerate(input_files):
            with open(file, "r", encoding="utf-8") as fin:
                reader = csv.reader(fin)
                header = next(reader)

                # Write header only for the first file
                if i == 0:
                    writer = csv.writer(fout)
                    writer.writerow(header)

                # Write the rest of the rows
                for row in reader:
                    writer.writerow(row)



input_files = [
    "jtl.csv",
    "lof.csv",
    "shd.csv",
    "sor.csv",
    "twi.csv"
]
output_file = "melded.csv"
merge_csv_files(input_files, output_file)
print(f"Merged {len(input_files)} files into {output_file}")

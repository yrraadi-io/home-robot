import gzip
import json
import sys


def main(input_filename, output_filename):
    # Load episodes from the gzip file
    episodes = json.load(gzip.open(input_filename))["episodes"]

    # Write episodes to the specified output JSON file
    with open(output_filename, "w") as outfile:
        json.dump(episodes, outfile, indent=4)

if __name__ == "__main__":
    # Check if the input and output file names are provided as command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_filename>.json.gz <output_filename>.json")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_filename = sys.argv[2]

    # Call the main function with the input and output filenames
    main(input_filename, output_filename)
"""
Helper script for generating a csv filled with random samples for multiple parameters
"""

import csv

import argparse

from random import randint


def compute_random_integers(num_ints, start=0, stop=100):
    """Returns num_ints random samples inside interval [start, stop]"""
    return [randint(start, stop) for idx in range(num_ints)]


def setup_argparse():
    parser = argparse.ArgumentParser(
        "csv_gen",
        description="Generate csv file fille with random integer samples for"
        " several different named parameters",
    )

    parser.add_argument(
        "-o",
        dest="csv_file",
        default="params.csv",
        help="Name of csv file to write out.",
    )

    parser.add_argument(
        "-n",
        "--num-values",
        default=20,
        type=int,
        help="Number of values to generate for each parameter"
    )

    parser.add_argument(
        "-p",
        "--params",
        nargs='+',
        default=['param1', 'param2', 'param3'],
    )

    parser.add_argument(
        "-d",
        "--debug",
        action='store_true',
        help="Print out parameter combinations as they're written"
    )

    parser.add_argument(
        "-i",
        "--index",
        default='',
        help="Optionally add an index column of the given name.  i.e. "
        "param_combo 1, param_combo 2, ..."
    )

    return parser


if __name__ == "__main__":

    parser = setup_argparse()

    args = parser.parse_args()

    print(args)

    params = {}
    for param in args.params:
        params[param] = compute_random_integers(num_ints=args.num_values)

    with open(args.csv_file, 'w') as csvfile:
        fieldnames = args.params

        if args.index:
            fieldnames = [args.index] + fieldnames
            print(f"Updated fieldnames: {fieldnames}")
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Invert into list of dicts and write out
        if args.debug:
            print("Writing params:")
        for idx, row in enumerate([dict(zip(params, row_vals)) for row_vals in zip(*params.values())]):

            # Add optional index column
            if args.index:
                row_to_write = {}
                row_to_write[args.index] = idx
                row_to_write.update(row)

            else:
                row_to_write = row

            writer.writerow(row_to_write)

            if args.debug:
                print(row_to_write)

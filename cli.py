"""
Command-line interface for tdxplot
by Eric Edwards, Alex JPS
2023-06-06

The primary .py file form which the program should run.
Parses user input via command-line arguments.
Also performs basic input validation (e.g. formatting, valid files, etc.)
Passes a dictionary with info to appropriate files or functions.
"""

# import libraries
import argparse
import sys
import os
import datetime

# import files
from report import *
from organization import *
from visual import *

# constants
COLORS: list[str] = ["white", "black", "gray", "yellow", "red", "blue", "green", "brown", "pink", "orange", "purple"] 
DATE_FORMATS: list[str] = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d.%m.%Y", "%d.%m.%Y"]
QUERY_TYPES = ["perweek", "perbuilding", "perroom"]

def check_file(filename: str):
    """
    Check that the given filename exists and is a CSV file.
    """
    if not filename:
        print("No file input provided", file=sys.stderr)
        exit(1)
    filename.strip()
    if not (os.path.exists(filename)):
        print("Always include filename as the last argument")
        print(f"File {filename} not found", file=sys.stderr)
        exit(1)
    if (os.path.splitext(filename)[-1].lower()) != ".csv":
            print("Always include filename as the last argument")
            print(f"File {filename} is not a CSV file", file=sys.stderr)
            exit(1)

def check_date(date_text: str):
    """
    Checks that given string adheres to one of DATE_FORMATS.
    Returns datetime object.
    """
    date = None
    for date_format in DATE_FORMATS:
        try:
            date: datetime = datetime.strptime(date_text, date_format)
            break
        except:
            continue
    if not date:
        print(f"Date {date_text} not recognized, try yyyy-mm-dd", file=sys.stderr)
        exit(1)
    return date

def set_query_type(args: dict) -> None:
    """
    Look at the mutually-exclusive args for query types.
    Set "querytype" value to the correct one.
    """
    for try_type in QUERY_TYPES:
        if args.get(try_type):
            if args.get("querytype"):
                print("Pass exactly one query type argument (e.g. --perweek)", file=sys.stderr)
                exit(1)
            args["querytype"] = try_type

def check_options(args: dict) -> None:
    """
    Halt program if conflicting or missing flags given.
    """
    # Stipulations for --perroom
    if args.get("perroom") and not args.get("building"):
        print("No building specified, please specify a building for --perroom using --building [BUILDING_NAME].", file=sys.stderr)
        exit(1)

    # Stipulations for --perbuilding
    if args.get("perbuilding") and args.get("building"):
        print("Cannot filter to a single building in in a --perbuilding query", file=sys.stderr)
        exit(1)

    # Stipulations for --perweek
    if not args.get("perweek") and args.get("weeks") != None:
        print("Cannot pass --weeks without --perweek", file=sys.stderr)
        exit(1)
    if args.get("weeks") and args.get("termend"):
        print("Cannot pass --weeks and --termend simultaneously", file=sys.stderr)
        exit(1)

def clean_args(args: dict, org: Organization) -> None:
    """
    Fix formatting by changing datatypes of some args.
    e.g. Change date-related args to datetime.
    """
    # ensure valid date formats
    if args.get("termstart"):
        args["termstart"] = check_date(args["termstart"])
    if args.get("termend"):
        args["termend"] = check_date(args["termend"])
    
    # use building object
    if args.get("building"):
        args["building"] = org.find_building(args["building"])
        if not args["building"]:
            print("No such building found in report", file=sys.stderr)
            exit(1)

def check_report(args: dict, report: Report) -> None:
    """
    For the requested query type,
    Halt program if report does not contain correct info.
    """
    query_type = args["querytype"]
    if query_type == "perweek":
        if "Created" not in report.fields_present:
            print("Cannot run a tickets-per-week query without Created field present in report", file=sys.stderr)
            exit(1)
    if query_type == "perbuilding":
        if "Class Support Building" not in report.fields_present:
            print("Cannot run a tickets-per-building query without Class Support Building field present in report", file=sys.stderr)
            exit(1)
    if query_type == "perroom":
        if ("Class Support Building" not in report.fields_present) or ("Room number" not in report.fields_present):
            print("Cannot run a tickets-per-room query without Class Support Building and Room number field present in report", file=sys.stderr)
            exit(1)

def parser_setup():
    """
    Set up argument parser with needed arguments.
    Return the parser.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    # display customization
    parser.add_argument("-n", "--name", type=str, help="Set the name of the plot.")
    parser.add_argument("-c", "--color", choices=COLORS, help="Set the color of the plot.")
    # filters
    parser.add_argument("-t", "--termstart", type=str, help="Exclude tickets before this date (calendar week for --perweek)")
    parser.add_argument("-e", "--termend", type=str, help="Exclude tickets after this date (calendar week for --perweek)")
    parser.add_argument("-w", "--weeks", type=int, help="Set number of weeks in the term for --perweek")
    parser.add_argument("-b", "--building", type=str, help="Specify building filter.")
    # query presets
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--perweek", action="store_true", help="Show tickets per week")
    query_group.add_argument("--perbuilding", action="store_true", help="Show tickets per building")
    query_group.add_argument("--perroom", action="store_true", help="Show tickets per room in a specified building.")
    
    return parser

def main():
    """
    Parse arguments, call basic input validation.
    Call plot.py with args.
    """
    # Check last arg is a valid filename
    filename: str = sys.argv.pop()
    filename.strip()
    check_file(filename)
    
    # set up parsers and parse into dict
    parser: argparse.ArgumentParser = parser_setup()
    args: dict = vars(parser.parse_args())

    # add missing info to args
    args["filename"] = filename

    # check for errors in args
    set_query_type(args)
    check_options(args)

    # initialize report
    report = Report(args["filename"])

    # populate organization
    org = Organization()
    report.populate(org)

    # FIXME refactor setting report fields to constructor, put me before previous block
    # check correct info present for query
    check_report(args, report)
    
    # clean up args dict with correct object types
    clean_args(args, org)

    # run query and display
    query_type = args["querytype"]
    if query_type == "perweek":
            tickets_per_week = org.per_week(args)
            view_per_week(tickets_per_week, args)
    if query_type == "perbuilding":
            tickets_per_building = org.per_building(args)
            print(tickets_per_building)
    if query_type == "perroom":
            tickets_per_room = org.per_room(args)
            print(tickets_per_room)
            
if __name__ == "__main__":
    main()

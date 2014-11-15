#!/usr/bin/env python3
__author__ = 'abrygunenko'
import sys
import re
from time import sleep
from urllib.request import urlopen
try:
    from chronyk import Chronyk
except ImportError:
    import pip
    pip.main(['install', 'chronyk'])
finally:
    from chronyk import Chronyk

_frequency = 3600  # frequency of beacon probe between --from and --too, currently in hours
_min_timestamp = 1378395540  # beacon start timestamp, could be 0 with current REST API implementation
_main_url = 'https://beacon.nist.gov/rest/record/'
_wrong_parameters_message = "\nWrong input parameters, please see help and try again."
_host_unreachable = "Host {0} is unreachable.".format(_main_url)
_host_unreachable_at_all = "\nHost {0} probably is down, exiting.".format(_main_url)
_value_not_found = "\nOutput value wasn't found in xml from {0}".format(_main_url)
_bad_time_received = "\nBad related time received, please see help and try again."
_from_less_than_to = "\nRelative time in --from should predate relative time in --to"
_time_less_than_min = "\nRelated time in --from or --to shouldn't predate beacon start at 09/05/2013 3:39 pm"
_out_of_memory = "\nProcess is out of memory, please choose smaller time period and try again."
_help_message = """
usage: summarize-beacon [--help] [--from "relative time"] [--to "relative time"]

Program is designed to get output values from
NIST Randomness Beacon REST API 'https://beacon.nist.gov/rest'
from relative time to relative time,
parse it and output every hexadecimal character
and number of it's occurrences from summarized beacon's output value.

Without arguments program will output every hexadecimal character
and number of it's occurrences in last Randomness Beacon output value.

optional arguments:
 --help  show this help message and exit
 --from  "relative time"
 --to    "relative time"

 If option --from is used, option --to is required after it.
 "relative time" string should look like:
 "2 year(s) 3 month(s) 2 day(s) 5 hour(s) 20 minute(s) ago",
 where at least one parameter is required
 (amount of years, months, days, hours or minutes)
 and "ago" in the end of the string.
 """


def get_xml(url):
    # getting xml from REST API
    xml = None
    for x in range(0, 3):  # try 3 times
        try:
            xml = str(urlopen(url).read())
            str_error = None
        except IOError as str_error:
            print(_host_unreachable)
            pass
        except ConnectionError as str_error:
            print(_host_unreachable)
            pass
        if str_error:
            print("Waiting 2 seconds for retry #{0}".format(x+1))
            sleep(2)  # wait for 2 seconds before trying to fetch the data again
            print("Retrying...")
        else:
            return xml
    print(_host_unreachable_at_all)
    sys.exit(1)


def parse_xml(xml):
    # parsing output value in xml received from REST API
    try:
        output_value = re.search('<outputValue>(.*?)</outputValue>', xml).group(1)
    except TypeError:
        print(_value_not_found)
        sys.exit(1)
    except ValueError:
        print(_value_not_found)
        sys.exit(1)
    else:
        return output_value


def validate_timestamps(from_timestamp, to_timestamp):
    # validating timestamps from related time received in --from and --to parameters
    if from_timestamp > to_timestamp:
        print(_from_less_than_to)
        sys.exit(1)
    elif from_timestamp < _min_timestamp or to_timestamp < _min_timestamp:
        print(_time_less_than_min)
        sys.exit(1)
    else:
        return True


def format_output_value(output_value):
    # printing formatted result
    output_value = ''.join(sorted(output_value))
    print("\nResult (hexadecimal character,number of occurrences in output value):")
    for symbol in output_value:
        counter = output_value.count(symbol)
        if counter > 0:
            print("{0},{1}".format(symbol, counter))
        output_value = output_value.replace(symbol, "")


def convert_to_timestamp(relative_time):
    # converting received relative time to timestamp
    try:
        timestamp = int(Chronyk(relative_time).timestamp())
    except TypeError:
        print(_bad_time_received)
        print(_help_message)
        sys.exit(1)
    except ValueError:
        print(_bad_time_received)
        print(_help_message)
        sys.exit(1)
    else:
        timestamp -= timestamp % 60
        return timestamp


def get_summary_record(from_timestamp, to_timestamp):
    # building timestamps list and summary output value
    timestamps_list = range(from_timestamp, to_timestamp, _frequency)
    output_data = ""
    for index, timestamp in enumerate(timestamps_list):
        timestamp_url = _main_url+str(timestamp)
        xml_from_timestamp = get_xml(timestamp_url)
        record_from_timestamp = parse_xml(xml_from_timestamp)
        try:
            output_data += record_from_timestamp
        except MemoryError:
            print(_out_of_memory)
            sys.exit(1)
        progress_bar(index, timestamps_list)
    return output_data


def progress_bar(iteration, data_list):
    # drawing progress bar
    one_percent = float(len(data_list)) / 100
    percent = (iteration + 1) / one_percent
    bar_length = 20
    hashes = '#' * int(bar_length*percent/100)
    spaces = ' ' * (bar_length - len(hashes))
    sys.stdout.write("\rGetting {0} records: [{1}] {2}%".format(len(data_list), hashes + spaces, round(percent, 1)))
    sys.stdout.flush()


def main():
    # main block, processing received arguments and general flow
    args = sys.argv[1:]
    if len(args) == 0:
        last_url = _main_url+'last/'
        last_xml = get_xml(last_url)
        last_record = parse_xml(last_xml)
        format_output_value(last_record)
    elif len(args) == 1:
        if not args[0] == "--help":
            print(_wrong_parameters_message)
            print(_help_message)
            sys.exit(2)
        print(_help_message)
        sys.exit(0)
    elif len(args) == 4:
        options = {}
        if not args[0] == "--from":
            print(_wrong_parameters_message)
            print(_help_message)
            sys.exit(2)
        options[args[0]] = args[1]
        if not args[2] == "--to":
            print(_wrong_parameters_message)
            print(_help_message)
            sys.exit(2)
        options[args[2]] = args[3]
        from_value = options['--from']
        to_value = options['--to']
        from_timestamp = convert_to_timestamp(from_value)
        to_timestamp = convert_to_timestamp(to_value)
        validate_timestamps(from_timestamp, to_timestamp)
        print("Requested records:\nFrom  {0}\nTo    {1}".format(Chronyk(from_value).ctime(), Chronyk(to_value).ctime()))
        try:
            summary_record = get_summary_record(from_timestamp, to_timestamp)
        except KeyboardInterrupt:
            print("\nProgram interrupted by user, exiting.")
            sys.exit(1)
        try:
            format_output_value(summary_record)
        except MemoryError:
            print(_out_of_memory)
            sys.exit(1)
    else:
        print(_wrong_parameters_message)
        print(_help_message)
        sys.exit(2)
    return True


if __name__ == '__main__':
    main()
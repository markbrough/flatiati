from flask import request, current_app
import json
import os
import unicodecsv
import datetime

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    return current_app.response_class(json.dumps(dict(*args, **kwargs),
            indent=None if request.is_xhr else 2, cls=JSONEncoder),
            mimetype='application/json')

def make_date_from_iso(iso_str):
    return datetime.date(int(iso_str[:4]), int(iso_str[5:7]),
                            int(iso_str[8:10]))

def exchange_rates():
    return {
        'GBP': 1.48446,
        'USD': 1,
        'CAD': 0.799941,
        'EUR': 1.12650,
        'AUD': 0.768543,
    }

def a_not_in_b(a, b):
    def filterer(a):
        return a[0] not in dict(b).keys()
    return filter(filterer, a)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def number_or_none(s):
    if s=="":
        return 0.00
    if is_number(s):
        return float(s)
    return None

def get_first(list):
    if list is None:
        return None
    return list[0]

def correct_zeros(value):
    if str(value) == "0.0":
        return "0"
    return value

def none_is_zero(value):
    try:
        return float(value)
    except TypeError:
        return 0.0
    return value

def correct_trailing_decimals(value):
    try:
        return int(value)
    except TypeError:
        return value

def filter_none_out(proj):
    return proj.capital_exp is not None

def filter_none_in(proj):
    return proj.capital_exp is None

def nulltoUnknown(value):
    if value == None:
        return "Inconnu"
    return value

def nulltoDash(value):
    if value == None:
        return "-"
    return value

def load_codelists():
    """Load codelists in that need to be changed"""

    def filter_csv(filename):
        if filename.endswith(".csv"):
            return True
        return False

    cl = filter(filter_csv, os.listdir("codelists"))
    codelists = {}
    for c in cl:
        csv = unicodecsv.DictReader(
                    open(os.path.join("codelists", c), "rb")
                    )
        codelist_name = c.split(".")[0]
        codelists[codelist_name] = {}
        for row in csv:
            codelists[codelist_name][row['2.01']] = row['1.0x']
    return codelists

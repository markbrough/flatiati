from flask import request, current_app
import json

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    return current_app.response_class(json.dumps(dict(*args, **kwargs),
            indent=None if request.is_xhr else 2, cls=JSONEncoder),
            mimetype='application/json')

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
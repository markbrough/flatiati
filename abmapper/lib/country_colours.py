import unicodecsv
from flask import escape

def colours(country_code):
    out = {}
    filename="abmapper/lib/colours_%s.csv" % escape(country_code)
    with open(filename, "r") as csvfile:
        csv = unicodecsv.DictReader(csvfile)
        for row in csv:
            out[row['name']] = row['colour']
    return out
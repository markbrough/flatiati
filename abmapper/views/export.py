from flask import send_file, jsonify
import xlrd, xlwt
import StringIO
import datetime
import unicodecsv
import re
from abmapper.query import projects as abprojects
from abmapper.query import stats as abstats
from abmapper.query import settings as absettings
from abmapper import app
from abmapper.lib import country_colours

def wm(ws, i, sectors_rows_length, col, value, style=None):
    if style:
        ws.write_merge(i, i+sectors_rows_length, col, col, value, style)
        return ws
    ws.write_merge(i, i+sectors_rows_length, col, col, value)
    return ws

def wr(ws, i, col, value, style=None):
    ws.write(i, col, value)
    return ws

def comma_join(attrA, attrB, list):
    return ",".join(map(lambda budget:
                 getattr(getattr(budget, attrA), attrB), list))

@app.route("/<country_code>/<reporting_org>/export.xls")
@app.route("/<country_code>/export.xls")
def activity_export(country_code, reporting_org=None):
    def notNone(value):
        if value is not None:
            return True
        return False

    def get_sectors_rows_length(numsectors):
        if numsectors > 0:
            return numsectors-1
        return 0

    def getcs_string(list, col):
        return "; ".join(filter(notNone, map(lambda x: getattr(x, col),
                                             list)))

    def getcs_org(list, col):
        return "; ".join(filter(notNone, map(lambda x:
                         getattr(x.organisation, col), list)))

    country_name = abprojects.country(country_code).text

    font0 = xlwt.Font()
    font0.name = 'Times New Roman'
    font0.bold = True
    styleHeader = xlwt.XFStyle()
    styleHeader.font = font0

    styleDates = xlwt.XFStyle()
    styleDates.num_format_str = 'YYYY-MM-DD'

    styleYellow = xlwt.XFStyle()
    yellowPattern = xlwt.Pattern()
    yellowPattern.pattern = xlwt.Pattern.SOLID_PATTERN
    yellowPattern.pattern_fore_colour = xlwt.Style.colour_map['yellow']
    styleYellow.pattern = yellowPattern

    styleRed = xlwt.XFStyle()
    redPattern = xlwt.Pattern()
    redPattern.pattern = xlwt.Pattern.SOLID_PATTERN
    redPattern.pattern_fore_colour = xlwt.Style.colour_map['red']
    styleRed.pattern = redPattern

    stylePCT = xlwt.XFStyle()
    stylePCT.num_format_str = '0%'

    def makeCCYellow(cc_id):
        if cc_id == "0":
            return True
        return False

    p = abprojects.projects(country_code, reporting_org)

    wb = xlwt.Workbook()
    ws = wb.add_sheet('Raw data export')
    headers = ['iati_identifier', 'project_title', 'project_description',
        'pct_{}'.format(country_name),
        'sector_code', 'sector_name', 'sector_pct', 'aid_type_code', 'aid_type',
        'activity_status_code', 'activity_status', 'date_start',
        'date_end', 'capital_spend_pct', 'total_commitments',
        'total_disbursements', 'budget_code', 'budget_name',
        'lowerbudget_code', 'lowerbudget_name', 'admin_code',
        'admin_name', 'loweradmin_code', 'loweradmin_name',
        'implementing_org']
    try:
        minFY, maxFY = abstats.earliest_latest_disbursements(country_code)
        disbFYs_QTRs = [("{} Q1".format(fy), "{} Q2".format(fy), "{} Q3".format(fy), "{} Q4".format(fy)) for fy in range(minFY, maxFY+1)]
        disbFYs = [item for sublist in disbFYs_QTRs for item in sublist]
        headers += map(lambda fy: "%s (D)" % fy, disbFYs)
    except ValueError:
        disbFYs = []
        pass

    [ws.write(0, i, h, styleHeader) for i, h in enumerate(headers)]

    i = 0

    for project in p:

        def remove_deleted_sectors(sector):
            return sector.deleted == False

        current_sectors = filter(remove_deleted_sectors, project.sectors)

        i+=1
        numsectors = len(current_sectors)
        sectors_rows_length = get_sectors_rows_length(numsectors)

        cols_vals = {
            0: project.iati_identifier,
            1: getcs_string(project.titles, 'text'),
            2: getcs_string(project.descriptions, 'text'),
            7: project.aid_type_code,
            8: project.aid_type.text,
            9: project.status_code,
            10: project.status.text,
            14: project.total_commitments,
            15: project.total_disbursements,
            24: getcs_org(project.implementing_orgs, 'name'),
        }
        for col, value in cols_vals.items():
            ws = wm(ws, i, sectors_rows_length, col, value)

        cols_vals_styles = {
            3: (project.this_country_pct/100.0, stylePCT),
            11: (project.date_start_actual or project.date_start_planned,
                 styleDates),
            12: (project.date_end_actual or project.date_end_planned,
                 styleDates),
            13: (project.capital_exp,
                 stylePCT),
        }

        for col, value in cols_vals_styles.items():
            ws = wm(ws, i, sectors_rows_length, col, value[0], value[1])

        for si, sector in enumerate(current_sectors):
            if not sector.assumed:
                ws.write(i, 4, sector.dacsector.code)
                ws.write(i, 5, sector.dacsector.description)
            else:
                if sector.formersector:
                    ws.write(i, 4, sector.formersector.code, styleRed)
                    ws.write(i, 5, sector.formersector.description,
                                                             styleRed)

            cols_vals_simple = {
                6: sector.percentage,
            }

            for col, value in cols_vals_simple.items():
                ws = wr(ws, i, col, value)

            for col, fy in enumerate(disbFYs, start=25):
                fyd = project.FY_disbursements_dict.get(str(fy))
                if fyd:
                    value = fyd["value"] * sector.percentage/100
                else:
                    value = 0
                ws.write(i, col, value)

            if si+1 < numsectors:
                i+=1

    strIOsender = StringIO.StringIO()
    wb.save(strIOsender)
    strIOsender.seek(0)
    reporting_org_obj = absettings.reporting_org_by_id(reporting_org)
    if reporting_org:
        the_filename = "aidonbudget_%s_%s.xls" % (country_code, reporting_org_obj.text)
    else:
        the_filename = "aidonbudget_%s.xls" % (country_code)
    return send_file(strIOsender,
                     attachment_filename=the_filename,
                     as_attachment=True)
                     
@app.route("/<country_code>/sankey.json")
def country_sankey(country_code):
    data = abstats.generate_sankey_data(country_code, "f")
    return jsonify(data)

@app.route("/<country_code>/budgetstats.csv")
def country_budget_stats_csv(country_code):

    fieldnames = ['budget_code', 'budget_name', 'before_value',
    'after_value', 'colour']
    strIOsender = StringIO.StringIO()
    writer = unicodecsv.DictWriter(strIOsender, fieldnames=fieldnames)
    writer.writeheader()

    def decomma(value):
        return re.sub(",", "", value)

    budget_stats = abstats.budget_project_stats(country_code, "f")

    ccolours = country_colours.colours(country_code)

    def get_colour(node, ccolours):
        if ccolours:
            if node in ccolours: return ccolours[node]
        return node

    for c, bs in budget_stats["budgets"].items():
        writer.writerow({"budget_code": bs["code"],
                          "budget_name": bs["name"],
                          "colour": get_colour(bs["name"], ccolours),
                          "before_value": decomma(bs["before"]["value"]),
                          "after_value": decomma(bs["after"]["value"])})
    strIOsender.seek(0)
    return send_file(strIOsender)

@app.route("/sectors/export.csv")
def sectors_stats_csv():
    data = abstats.sectors_stats()
    strIOsender = StringIO.StringIO()
    fieldnames = ['sector_code', 'sector_description',
      'sector_parent_code', 'countries', 'total_value', 'num_activities']
    writer = unicodecsv.DictWriter(strIOsender, fieldnames=fieldnames)
    writer.writeheader()
    for stats in data:
        writer.writerow(stats)
    strIOsender.seek(0)
    return send_file(strIOsender)

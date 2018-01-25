from flask import send_file, jsonify, abort
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
    if style:
        ws.write(i, col, value, style)
    ws.write(i, col, value)
    return ws

def comma_join(attrA, attrB, list):
    return ",".join(map(lambda budget:
                 getattr(getattr(budget, attrA), attrB), list))

@app.route("/<lang>/countries/<country_code>/<reporting_org>/export.xls")
@app.route("/<lang>/countries/<country_code>/export.xls")
def activity_export(country_code, reporting_org=None, lang="en"):
    def notNone(value):
        if value is not None:
            return True
        return False

    def get_sectors_rows_length(numsectors):
        if numsectors > 0:
            return numsectors-1
        return 0

    def getcs_string(list, col):
        return "; ".join(filter(notNone, map(lambda x: unicode(getattr(x, col)),
                                             list)))

    def getcs_org(list, col):
        return "; ".join(filter(notNone, map(lambda x:
                         getattr(x.organisation, col), list)))

    country = abprojects.country(country_code)
    country_name = country.text

    font0 = xlwt.Font()
    font0.name = 'Times New Roman'
    font0.bold = True
    styleHeader = xlwt.XFStyle()
    styleHeader.font = font0

    styleDates = xlwt.XFStyle()
    styleDates.num_format_str = 'YYYY-MM-DD'

    stylePCT = xlwt.XFStyle()
    stylePCT.num_format_str = '0%'

    projects = abprojects.projects(country_code, reporting_org)

    wb = xlwt.Workbook()
    ws = wb.add_sheet('Raw data export')
    
    headers = ['iati_identifier', 'project_title', 'project_description',
        u'pct_{}'.format(country_name),
        'sector_code', 'sector_name', 'sector_pct', 'aid_type_code', 'aid_type',
        'collaboration_type_code','collaboration_type','finance_type_code',
        'finance_type',
        'activity_status_code', 'activity_status', 'date_start',
        'date_end', 'capital_spend_pct', 'total_commitments',
        'total_disbursements',
        'implementing_org']
    try:
        minFY, maxFY = abstats.earliest_latest_disbursements(country_code)
        disbFYs_QTRs = [("{} Q1".format(fy), "{} Q2".format(fy), 
                         "{} Q3".format(fy), "{} Q4".format(fy)
                         ) for fy in range(minFY, maxFY+1)]
        disbFYs = [item for sublist in disbFYs_QTRs for item in sublist]
        headers += map(lambda fy: "%s (D)" % fy, disbFYs)
    except ValueError:
        disbFYs = []
        pass

    minFY_fwd, maxFY_fwd = abstats.earliest_latest_forward_data(country_code)
    fwdFYs = [fy for fy in range(minFY_fwd, maxFY_fwd+1)]
    headers += map(lambda fy: "MTEF {}".format(fy), fwdFYs)

    [ws.write(0, i, h, styleHeader) for i, h in enumerate(headers)]

    i = 0

    for project in projects:

        def remove_deleted_sectors(sector):
            return sector.deleted == False

        current_sectors = filter(remove_deleted_sectors, project.sectors)

        i+=1
        numsectors = len(current_sectors)
        sectors_rows_length = get_sectors_rows_length(numsectors)

        cols_vals = {
            0: (project.iati_identifier, None),
            1: (getcs_string(project.titles, 'text'), None),
            2: (getcs_string(project.descriptions, 'text'), None),
            3: (project.country_pcts_float[country.code]/100.0, stylePCT),
            7: (project.aid_type_code, None),
            8: (project.aid_type.text, None),
            9: (project.collaboration_type.code, None),
            10: (project.collaboration_type.text, None),
            11: (getcs_string(project.finance_types, 'code'), None),
            12: (getcs_string(project.finance_types, 'text'), None),
            13: (project.status_code, None),
            14: (project.status.text, None),
            15: (project.date_start_actual or project.date_start_planned,
                 styleDates),
            16: (project.date_end_actual or project.date_end_planned,
                 styleDates),
            17: (project.capital_exp, None),
            18: (project.total_commitments, None),
            19: (project.total_disbursements, None),
            20: (getcs_org(project.implementing_orgs, 'name'), None),
        }

        for col, value in cols_vals.items():
            if value[1] != None:
                ws = wm(ws, i, sectors_rows_length, col, value[0], value[1])
            else:
                ws = wm(ws, i, sectors_rows_length, col, value[0])

        for si, sector in enumerate(current_sectors):
            cols_vals_simple = {
                4: sector.dacsector.code,
                5: sector.dacsector.description,
                6: sector.percentage,
            }

            for col, value in cols_vals_simple.items():
                ws = wr(ws, i, col, value)

            for col, fy in enumerate(disbFYs, start=21):
                fyd = project.FY_disbursements_dict(country).get(str(fy))
                if fyd:
                    value = fyd["value"] * sector.percentage/100.0
                else:
                    value = 0
                ws.write(i, col, value)

            for col, fy in enumerate(fwdFYs, start=21+len(disbFYs)):
                fyd = project.FY_forward_spend_dict(country).get(str(fy))
                if fyd:
                    value = fyd["value"] * sector.percentage/100.0
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

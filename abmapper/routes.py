from flask import Flask, render_template, flash, request, Markup, \
    session, redirect, url_for, escape, Response, abort, send_file

from abmapper import app
from abmapper import db
import models
from datastore import download
import projects
import setup as absetup
import util
import xlwt
import StringIO
import datetime

@app.route("/")
def dashboard():
    countries=projects.countries_activities()
    return render_template("dashboard.html",
                           countries=countries,
                          )

@app.route("/<country_code>/")
def home(country_code):
    p = projects.projects(country_code)
    stats = projects.country_project_stats(country_code)
    country = projects.country(country_code)
    reporting_orgs = projects.reporting_org_activities(country_code)
    return render_template("country.html",
                           projects=p,
                           country=country,
                           reporting_orgs=reporting_orgs,
                           stats=stats,
                           )

@app.route("/<country_code>/activities/<iati_identifier>/")
def activities(country_code, iati_identifier):
    a = projects.project(iati_identifier)
    country = projects.country(country_code)
    sectors = projects.DAC_codes_cc_mappable()
    return render_template("project.html",
                           activity=a,
                           sectors=sectors,
                           country=country,
                           )

@app.route("/<country_code>/activities/<path:iati_identifier>/addsector/", methods=['POST'])
def activity_add_sector(country_code, iati_identifier):
    sector_code = request.form['sector_code']
    iati_identifier = request.form['iati_identifier']
    percentage = request.form['percentage']
    sector_data = projects.sector(sector_code)

    if projects.add_sector_to_project(sector_code, iati_identifier, percentage):
        return util.jsonify({"cc": {
                               "sector": sector_data.sector, 
                               "function": sector_data.function, 
                               "id": sector_data.id
                             },
                             "description": sector_data.description,
                            })
    return util.jsonify({"error":True})

@app.route("/<country_code>/activities/<path:iati_identifier>/deletesector/", methods=['POST'])
def activity_delete_sector(country_code, iati_identifier):
    sector_code = request.form['sector_code']
    iati_identifier = iati_identifier
    result = projects.delete_sector_from_project(sector_code, iati_identifier)
    if result:
        return util.jsonify({"success": result})
    return util.jsonify({"error": True})

@app.route("/<country_code>/activities/<path:iati_identifier>/restoresector/", methods=['POST'])
def activity_restore_sector(country_code, iati_identifier):
    sector_code = request.form['sector_code']
    iati_identifier = iati_identifier
    if projects.restore_sector_to_project(sector_code, iati_identifier):
        return util.jsonify({"success": True})
    return util.jsonify({"error": True})

@app.route("/<country_code>/<reporting_org>/export.xls")
@app.route("/<country_code>/export.xls")
def activity_export(country_code, reporting_org=None):
    def notNone(value):
        if value is not None:
            return True
        return False

    def getcs_string(list, col):
        return "; ".join(filter(notNone, map(lambda x: getattr(x, col), list)))

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

    stylePCT = xlwt.XFStyle()
    stylePCT.num_format_str = '0%'

    def makeCCYellow(cc_id):
        if cc_id == "0":
            return True
        return False

    p = projects.projects(country_code, reporting_org)

    wb = xlwt.Workbook()
    ws = wb.add_sheet('Raw data export')
    headers = ['iati_identifier', 'project_title', 'project_description', 
        'sector_code', 'sector_name', 'sector_pct', 'cc_id', 'aid_type_code',
        'aid_type', 'activity_status_code', 'activity_status', 'date_start', 
        'date_end', 'capital_spend_pct', 'total_commitments', 
        'total_disbursements', 'budget_code', 'budget_name', 'lowerbudget_code',
        'lowerbudget_name']

    for i, h in enumerate(headers):
        ws.write(0, i, h, styleHeader)

    i = 0

    for project in p:

        def remove_deleted_sectors(sector):
            return sector.deleted == False

        current_sectors = filter(remove_deleted_sectors, project.sectors)

        i+=1
        numsectors = len(current_sectors)
        ws.write_merge(i, i+numsectors-1, 0, 0, project.iati_identifier)
        ws.write_merge(i, i+numsectors-1, 1, 1, getcs_string(project.titles, 'text'))
        ws.write_merge(i, i+numsectors-1, 2, 2, getcs_string(project.descriptions, 'text'))
        ws.write_merge(i, i+numsectors-1, 7, 7, project.aid_type_code)
        ws.write_merge(i, i+numsectors-1, 8, 8, project.aid_type.text)
        ws.write_merge(i, i+numsectors-1, 9, 9, project.status_code)
        ws.write_merge(i, i+numsectors-1, 10, 10, project.status.text)
        ws.write_merge(i, i+numsectors-1, 11, 11, project.date_start_actual or
                                        project.date_start_planned, styleDates)
        ws.write_merge(i, i+numsectors-1, 12, 12, project.date_end_actual or 
                                        project.date_end_planned, styleDates)
        ws.write_merge(i, i+numsectors-1, 13, 13, project.capital_exp, stylePCT)
        ws.write_merge(i, i+numsectors-1, 14, 14, project.total_commitments)
        ws.write_merge(i, i+numsectors-1, 15, 15, project.total_disbursements)

        def frelbudget(budget_code):
            return project.recipient_country_code == budget_code.budgetcode.country_code

        def frelbudgetlow(budget_code):
            return project.recipient_country_code == budget_code.lowerbudgetcode.country_code

        for si, sector in enumerate(current_sectors):
            ws.write(i, 3, sector.dacsector.code)
            ws.write(i, 4, sector.dacsector.description)
            ws.write(i, 5, sector.percentage)
            if makeCCYellow(sector.dacsector.cc.id):
                ws.write(i, 6, sector.dacsector.cc.id, styleYellow)
            else:
                ws.write(i, 6, sector.dacsector.cc.id)
        
            relevant_budget = filter(frelbudget, sector.dacsector.cc.cc_budgetcode)
            relevant_lowerbudget = filter(frelbudgetlow, sector.dacsector.cc.cc_lowerbudgetcode)

            budget_codes = ",".join(map(lambda budget: budget.budgetcode.code, relevant_budget))
            budget_names = ",".join(map(lambda budget: budget.budgetcode.name, relevant_budget))
            lowerbudget_codes = ",".join(map(lambda budget: budget.lowerbudgetcode.code, relevant_lowerbudget))
            lowerbudget_names = ",".join(map(lambda budget: budget.lowerbudgetcode.name, relevant_lowerbudget))

            ws.write(i, 16, budget_codes)
            ws.write(i, 17, budget_names)
            ws.write(i, 18, lowerbudget_codes)
            ws.write(i, 19, lowerbudget_names)
                
            if si+1 < numsectors:
                i+=1



    strIOsender = StringIO.StringIO()
    wb.save(strIOsender)
    strIOsender.seek(0)
    if reporting_org:
        the_filename = "aidonbudget_%s_%s.xls" % (country_code, reporting_org)
    else:
        the_filename = "aidonbudget_%s.xls" % (country_code)
    return send_file(strIOsender,
                     attachment_filename=the_filename,
                     as_attachment=True)

@app.route("/setup/")
@app.route("/setup/<lang>/")
def setup(lang="EN"):
    absetup.setup(lang)
    return "OK"

@app.route("/import/<country>/")
def importer():
    download.parse_file("iati_data_"+country+".xml")
    return "OK"

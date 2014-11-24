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
    country = projects.country(country_code)
    reporting_orgs = projects.reporting_org_activities(country_code)
    return render_template("country.html",
                           projects=p,
                           country=country,
                           reporting_orgs=reporting_orgs,
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
        'total_disbursements']

    for i, h in enumerate(headers):
        ws.write(0, i, h, styleHeader)

    i = 0
    for project in p:
        i+=1
        numsectors = len(project.sectors)
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
        ws.write_merge(i, i+numsectors-1, 13, 13, 0.00)
        ws.write_merge(i, i+numsectors-1, 14, 14, project.total_commitments)
        ws.write_merge(i, i+numsectors-1, 15, 15, project.total_disbursements)
        for si, sector in enumerate(project.sectors):
            if sector.deleted:
                continue
            ws.write(i, 3, sector.dacsector.code)
            ws.write(i, 4, sector.dacsector.description)
            ws.write(i, 5, sector.percentage)
            if makeCCYellow(sector.dacsector.cc.id):
                ws.write(i, 6, sector.dacsector.cc.id, styleYellow)
            else:
                ws.write(i, 6, sector.dacsector.cc.id)
                
            if si+1 < numsectors:
                i+=1

    strIOsender = StringIO.StringIO()
    wb.save(strIOsender)
    strIOsender.seek(0)
    return send_file(strIOsender,
                     attachment_filename="export.xls",
                     as_attachment=True)

@app.route("/setup/")
def setup():
    absetup.setup()
    return "OK"

@app.route("/import/<country>/")
def importer():
    download.parse_file("iati_data_"+country+".xml")
    return "OK"

from flask import render_template, request
from abmapper import app
from abmapper.lib import util
from abmapper.query import projects as abprojects
from abmapper.query import sectors as absectors

@app.route("/<country_code>/activities/<iati_identifier>/")
def activities(country_code, iati_identifier):
    a = abprojects.project(iati_identifier)
    country = abprojects.country(country_code)
    sectors = absectors.DAC_codes_cc_mappable()
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
    sector_data = absectors.sector(sector_code)

    if absectors.add_sector_to_project(sector_code, iati_identifier, percentage):
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
    result = absectors.delete_sector_from_project(sector_code, iati_identifier)
    if result:
        return util.jsonify({"success": result})
    return util.jsonify({"error": True})

@app.route("/<country_code>/activities/<path:iati_identifier>/restoresector/", methods=['POST'])
def activity_restore_sector(country_code, iati_identifier):
    sector_code = request.form['sector_code']
    iati_identifier = iati_identifier
    if absectors.restore_sector_to_project(sector_code, iati_identifier):
        return util.jsonify({"success": True})
    return util.jsonify({"error": True})
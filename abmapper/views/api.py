from flask import Flask, render_template, flash, request, Markup, \
    session, redirect, url_for, escape, Response, abort, send_file, \
    jsonify, current_app
                            
from abmapper import app, db, models
from abmapper.query import settings as qsettings
import datetime, json

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if (isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    return current_app.response_class(json.dumps(dict(*args, **kwargs),
            indent=None if request.is_xhr else 2, cls=JSONEncoder),
        mimetype='application/json')

@app.route("/api/reporting_orgs/", methods=["POST", "GET"])
def api_reporting_orgs():
    """GET returns a list of all financial data for a given activity_id. 
    
    POST also accepts financial data to be added or deleted."""
    
    if request.method == "POST":
        if request.form["action"] == "add":
            result = qsettings.add_reporting_org("")
        elif request.form["action"] == "delete":
            result = qsettings.delete_reporting_org(request.form["reporting_org_id"])
        return str(result)
    elif request.method == "GET":
        reporting_orgs = list(map(lambda x: x.as_dict(), 
                         qsettings.reporting_orgs()))
        return jsonify(reporting_orgs = reporting_orgs)

@app.route("/api/update_reporting_org/", methods=['POST'])
def api_update_reporting_org_attr():
    data = {
        'attr': request.form['attr'],
        'value': request.form['value'],
        'reporting_org_id': request.form['reporting_org_id'],
    }
    if data["value"] == u"true":
        data["value"] = True
    elif data["value"] == u"false":
        data["value"] = False
    update_status = qsettings.update_reporting_org_attr(data)
    if update_status == True:
        return "success"
    return "error"

from flask import render_template, request
import abmapper
from abmapper import app
from abmapper.lib import util
from abmapper.query import projects as abprojects
from abmapper.query import sectors as absectors

@app.route("/<lang>/countries/<country_code>/activities/<path:iati_identifier>/")
def activities(country_code, iati_identifier, lang="en"):
    abmapper.set_lang(lang)
    a = abprojects.project(iati_identifier)
    country = abprojects.country(country_code)
    page_args = request.view_args
    page_args.pop("lang")
    return render_template("project.html",
                           activity=a,
                           country=country,
                           freeze=('FREEZE' in app.config),
                           lang=lang,
                           page_endpoint = request.endpoint,
                           page_args = page_args,
                           )

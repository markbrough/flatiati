from flask import render_template, request, redirect, url_for
import abmapper
from abmapper import app
from abmapper.query import projects as abprojects
from abmapper.query import stats as abstats

@app.route("/")
def dashboard_en(lang="en"):
    return redirect(url_for("dashboard", lang="en"))

@app.route("/<lang>/")
def dashboard(lang="en"):
    abmapper.set_lang(lang)
    countries=abprojects.countries_activities()
    page_args = request.view_args
    page_args.pop("lang")
    return render_template("dashboard.html",
                           countries=countries,
                           freeze=('FREEZE' in app.config),
                           lang=lang,
                           page_endpoint = request.endpoint,
                           page_args = page_args,
                          )

@app.route("/<lang>/countries/<country_code>/")
def country_home(country_code, lang="en"):
    abmapper.set_lang(lang)
    stats = abstats.country_project_stats(country_code)
    country = abprojects.country(country_code)
    reporting_orgs = abprojects.reporting_org_activities(country_code)
    page_args = request.view_args
    page_args.pop("lang")
    return render_template("country.html",
                           country=country,
                           reporting_orgs=reporting_orgs,
                           stats=stats,
                           freeze=('FREEZE' in app.config),
                           config = app.config,
                           lang=lang,
                           page_endpoint = request.endpoint,
                           page_args = page_args,
                           )

@app.route("/<lang>/countries/<country_code>/activities/")
def country_activities(country_code, lang="en"):
    abmapper.set_lang(lang)
    p = abprojects.projects(country_code)
    country = abprojects.country(country_code)
    reporting_orgs = abprojects.reporting_org_activities(country_code)
    page_args = request.view_args
    page_args.pop("lang")
    return render_template("country_activities.html",
                           projects=p,
                           country=country,
                           reporting_orgs=reporting_orgs,
                           freeze=('FREEZE' in app.config),
                           lang=lang,
                           page_endpoint = request.endpoint,
                           page_args = page_args,
                           )
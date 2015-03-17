from flask import render_template
from abmapper import app
from abmapper.query import projects as abprojects

@app.route("/")
def dashboard():
    countries=abprojects.countries_activities()
    return render_template("dashboard.html",
                           countries=countries,
                          )

@app.route("/<country_code>/")
def country_home(country_code):
    stats = abprojects.country_project_stats(country_code)
    budget_stats = abprojects.budget_project_stats(country_code)
    country = abprojects.country(country_code)
    reporting_orgs = abprojects.reporting_org_activities(country_code)
    return render_template("country.html",
                           country=country,
                           reporting_orgs=reporting_orgs,
                           stats=stats,
                           budget_stats=budget_stats,
                           )

@app.route("/<country_code>/activities/")
def country_activities(country_code):
    p = abprojects.projects(country_code)
    country = abprojects.country(country_code)
    reporting_orgs = abprojects.reporting_org_activities(country_code)
    return render_template("country_activities.html",
                           projects=p,
                           country=country,
                           reporting_orgs=reporting_orgs,
                           )
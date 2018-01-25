from flask import render_template, request, flash, url_for, redirect
from abmapper import app, db
from abmapper.lib import util
from abmapper.query import projects as abprojects
from abmapper.query import settings as absettings
from abmapper.datastore import download
import exchangerates

@app.route("/<lang>/admin/")
def admin(lang="en"):
    page_args = request.view_args
    page_args.pop("lang")
    return render_template("admin.html",
            api_reporting_orgs_url = url_for('api_reporting_orgs'),
            api_update_reporting_orgs_url = url_for('api_update_reporting_org_attr'),
           lang=lang,
           page_endpoint = request.endpoint,
           page_args = page_args,
          )

@app.route("/admin/update_exchange_rates/", methods=['POST'])
def admin_update_exchange_rates():
    exchangerates.CurrencyConverter(update=True)
    flash("Updated exchange rates", "success")
    return redirect(url_for("admin"))

@app.route("/<lang>/<country_code>/settings/", methods=['GET', 'POST'])
def country_settings(country_code, lang="en"):
    if request.method == "GET":
        country = abprojects.country(country_code)
        reporting_orgs = absettings.reporting_orgs()
        page_args = request.view_args
        page_args.pop("lang")
        return render_template("country_settings.html",
                               country=country,
                               reporting_orgs = reporting_orgs,
                               lang=lang,
                               page_endpoint = request.endpoint,
                               page_args = page_args,
                               )
    elif request.method == "POST":
        if "settings" in request.form:
            country = abprojects.country(country_code)
            country.fiscalyear_modifier = request.form["fiscalyear_modifier"]
            db.session.commit()
            flash("Updated fiscal year start", "success")
        elif "fetch_reporting_org" in request.form:
            country = abprojects.country(country_code)
            download.download_data(country.code, request.form["reporting_org_ref"])
            flash("Retrieved data for {}".format(request.form["reporting_org_ref"]), "success")
        elif "fetch_all_reporting_orgs" in request.form:
            orgs = absettings.reporting_orgs()
            print ""
            print "Download and import data"
            for org in orgs:
                if org.active == True:
                    print ""
                    print """Downloading IATI XML for reporting organisation {}""".format(org.text_EN)
                    download.download_data(org.code)
                    flash("Retrieved data for {}".format(org.text_EN), "success")
        return redirect(url_for("country_settings", 
                                country_code=country_code, lang=lang))

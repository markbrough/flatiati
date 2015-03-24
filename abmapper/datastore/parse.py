from lxml import etree
import os
from abmapper import app, db
from abmapper.query import projects as abprojects
from abmapper.query import models
import datetime


DAC_codes = abprojects.DAC_codes()

def getfirst(list):
    if len(list)>0:
        return list[0]
    return None

def getDACSectors(sectors):
    out = []
    for sector in sectors:
        code = getfirst(sector.xpath('@code'))
        percentage = getfirst(sector.xpath('@percentage'))
        if not checkDAC(code): continue
        out.append({
            'code': code,
            'percentage': percentage})
    return out, len(out)

def checkDAC(code):
    try:
        code = int(code)
    except ValueError:
        return False
    return code in DAC_codes

def get_sectors(activity):
    s = []
    sectors=activity.xpath(
        'sector[@vocabulary="DAC"]|sector[not(@vocabulary)]')
    sectors, num_sectors=getDACSectors(sectors)
    for sector in sectors:
        ns = models.Sector()
        ns.code = sector['code']
        ns.percentage = sector['percentage'] or 100
        s.append(ns)
    return s

def parse_org(xml):
    data = {
        "ref": xml.get("ref", ""),
        "name": getfirst(xml.xpath('text()')),
        "type": xml.get("@type")
        }
    if not data.get("ref") and not data.get("name"):
        return False
    check = models.Organisation.query.filter_by(
        ref = data["ref"],
        name = data["name"]
    ).first()
    if check: return check
    return models.Organisation.as_unique(db.session, **data)

def get_orgs(activity):
    ret = []
    seen = set()
    for ele in activity.xpath("./participating-org"):
        role = ele.get("role", "Funding")
        organisation = parse_org(ele)
        if organisation and not (role, organisation.name) in seen:
            seen.add((role, organisation.name))
            ret.append(models.Participation(role=role,
                      organisation=organisation))
    return ret

def get_transactions(activity):
    ret = []
    for ele in activity.xpath("./transaction"):
        t_type = getfirst(ele.xpath("transaction-type/@code"))
        t_date = getfirst(ele.xpath("transaction-date/@iso-date"))
        t_value = getfirst(ele.xpath("value/text()"))
        t_value_date = getfirst(ele.xpath("value/@value-date"))
        
        #FIXME for WB data which puts t_date in the wrong place
        if activity.xpath("reporting-org/@ref='US'"):
            t_date = t_value_date
        
        #FIXME for US data which doesn't include a t_date
        if activity.xpath("reporting-org/@ref='44000'"):
            t_date = getfirst(ele.xpath("transaction-date/@value-date"))

        if not (t_type and t_date and t_value and t_value_date): 
            print "woah, transaction doesn't look right"
            print "Extending org is", activity.xpath("participating-org[@role='Extending']/@ref")
            print "t_type is", t_type
            print "t_date is", t_date
            print "t_value is", t_value
            print "t_value_date is", t_value_date
            continue

        iati_identifier = getfirst(activity.xpath("iati-identifier/text()"))

        tr = models.Transaction()
        tr.activity_iati_identifier = iati_identifier
        tr.value = t_value
        tr.value_date = datetime.datetime.strptime(
                t_value_date, "%Y-%m-%d" )
        tr.value_currency = ""
        tr.transaction_date = datetime.datetime.strptime(
                t_date, "%Y-%m-%d" )
        tr.transaction_type_code = t_type
        ret.append(tr)
    return ret 

def get_titles(activity):
    ret = []
    for ele in activity.xpath("./title"):
        title = models.Title()
        title.text = ele.text
        title.lang = getfirst(ele.xpath('@xml:lang'))
        ret.append(title)
    return ret

def get_descriptions(activity):
    ret = []
    for ele in activity.xpath("./description"):
        description = models.Description()
        description.text = ele.text
        description.lang = getfirst(ele.xpath('@xml:lang'))
        ret.append(description)
    return ret

def get_date(activity, date_type):
    date_value = getfirst(
        activity.xpath('activity-date[@type="'+date_type+'"]/@iso-date')
        )
    if not date_value:
        return None
    return datetime.datetime.strptime(
        date_value,
        "%Y-%m-%d" )
        
def null_to_default(value, default):
    if value is None:
        return default
    return value

def write_activity(activity, country_code):
    a = models.Activity()
    a.iati_identifier = getfirst(activity.xpath('iati-identifier/text()'))
    a.all_titles = get_titles(activity)
    a.all_descriptions = get_descriptions(activity)
    a.sectors = get_sectors(activity)
    a.participating_orgs = get_orgs(activity)
    a.reporting_org_ref = getfirst(activity.xpath('reporting-org/@ref'))
    a.transactions = get_transactions(activity)
    a.status_code = null_to_default(
        getfirst(activity.xpath('activity-status/@code')),
        "2"
        )
    a.aid_type_code = null_to_default(
getfirst(activity.xpath('default-aid-type/@code|transaction/aid-type/@code')),
        "C01"
        )
    a.date_start_planned = get_date(activity, 'start-planned')
    a.date_end_planned = get_date(activity, 'end-planned')
    a.date_start_actual = get_date(activity, 'start-actual')
    a.date_end_actual = get_date(activity, 'end-actual')
    a.recipient_country_code = country_code
    db.session.add(a)
    db.session.commit()

def parse_file(country_code, filename):
    LOCAL_DIR=app.config["DATA_STORAGE_DIR"]
    path = os.path.join(LOCAL_DIR, filename)
    doc=etree.parse(path)
    activities = doc.xpath('//iati-activity')
    for i, activity in enumerate(activities):
        write_activity(activity, country_code)
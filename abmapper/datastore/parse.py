from lxml import etree
import os
from abmapper import app, db
from abmapper.query import projects as abprojects
from abmapper.query import sectors as absectors
from abmapper.query import settings as absettings
from abmapper.query import models
from abmapper.lib import util, codelists
import exchangerates
import datetime
import flattener, flatten_rules
import sqlalchemy as sa
from flask import flash
from dateutil.parser import parse as dtparse
from collections import defaultdict

class UnrecognisedVersionException(Exception):
    pass

class InvalidFormatException(Exception):
    pass

def get_alt(list_1, list_2):
    if list_1:
        return list_1[0]
    if list_2:
        return list_2[0]
    return None

def getfirst(list, default=None):
    if len(list)>0:
        return list[0]
    return default

def getDACSectors(sectors):
    DAC_codes = absectors.DAC_codes()
    out = []
    for sector in sectors:
        code = getfirst(sector.xpath('@code'))
        percentage = getfirst(sector.xpath('@percentage'))
        if not checkDAC(code, DAC_codes): continue
        out.append({
            'code': unicode(code),
            'percentage': percentage})
    return out, len(out)

def checkDAC(code, DAC_codes):
    try:
        code = int(code)
    except ValueError:
        return False
    return code in DAC_codes

def get_recipient_countries(activity):
    rcs = []
    countries=activity.xpath(
        'recipient-country')
    for country in countries:
        rc = models.RecipientCountries()
        rc.recipient_country_code = avoidIntegrityError(
            unicode(country.get("code")), "Country", "0")
        rc.percentage = country.get("percentage", 100)
        rcs.append(rc)
    return rcs

def get_sectors_from_transactions(activity, version):
    codes = { 2: "2", 1: "C" }
    vocabs = { 2: "1", 1: "DAC" }

    trans = activity.xpath("transaction[transaction-type/@code='{}']".format(codes[version]))
    codes_values = list(map(lambda t: (
                float(t.find("value").text),
                str(getfirst(t.xpath("sector[@vocabulary='{}']/@code|sector[not(@vocabulary)]/@code".format(vocabs[version]))))
                ), trans))
    total_value = sum(map(lambda x: x[0], codes_values))
    if total_value == 0:
        return []
    d = defaultdict(list)
    for value, code in codes_values:
        d[code].append(value)
    return list(map(lambda s: {"code": s[0], "percentage": round(sum(s[1])/total_value*100, 2)}, d.items()))

def get_sectors(activity, version):
    s = []
    sectors=activity.xpath(
        'sector[@vocabulary="DAC"]|sector[not(@vocabulary)]|sector[@vocabulary="1"]')
    sectors, num_sectors=getDACSectors(sectors)

    if num_sectors == 0:
        sectors = get_sectors_from_transactions(activity, version)

    for sector in sectors:
        ns = models.Sector()
        ns.code = avoidIntegrityError(
                    unicode(sector['code']), "Sector", "0")
        ns.percentage = sector['percentage'] or 100
        s.append(ns)
    return s

def parse_org(xml, version):
    data = {
        "ref": unicode(xml.get("ref", "")),
        "name": unicode(getfirst(xml.xpath('text()'))),
        "type": unicode(xml.get("@type"))
        }
    #FIXME: Need to make this properly multilingual where organisations can be published in multiple names
    if version == 2: 
        data["name"] = unicode(getfirst(xml.xpath("narrative/text()")))
    if not data.get("ref") and not data.get("name"):
        return False
    check = models.Organisation.query.filter_by(
        ref = data["ref"],
        name = data["name"]
    ).first()
    if check: return check
    return models.Organisation.as_unique(db.session, **data)

def get_o_role(value):
    try:
        types = {
            "1": u"Funding",
            "2": u"Accountable",
            "3": u"Extending",
            "4": u"Implementing"
        }
        return types[value]
    except KeyError:
        raise InvalidFormatException("""{} is not a valid participating 
        organisation role for this version of the IATI Standard""")

def get_orgs(activity, version):
    ret = []
    seen = set()
    for ele in activity.xpath("./participating-org"):
        role = unicode(ele.get("role", {1: u"Funding", 2: u"1"}[version]))
        if version == 2:
            role = get_o_role(role)
        organisation = parse_org(ele, version)
        if organisation and not (role, organisation.name) in seen:
            seen.add((role, organisation.name))
            ret.append(models.Participation(role=role,
                      organisation=organisation))
    return ret

def get_currency(activity, transaction):
    ac = activity.get("default-currency")
    if ac and ac != "":
        return unicode(ac)
    tc = transaction.xpath("value/@currency")
    if tc and tc != "":
        return unicode(tc)
    return u"USD"

def get_t_type(value):
    try:
        types = {
            "1": u"IF",
            "2": u"C",
            "3": u"D",
            "4": u"E",
            "5": u"IR",
            "6": u"LR",
            "7": u"R",
            "8": u"QP",
            "9": u"Q3",
            "10": u"CG",
            "11": u"IC"
        }
        return types[value]
    except KeyError:
        raise InvalidFormatException("""{} is not a valid transaction type 
        for this version of the IATI Standard""")

def get_fiscal_periods(start_date, end_date):
    quarters = {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4}
    start_year, start_qtr = start_date.year, quarters[start_date.month]
    end_year, end_qtr = end_date.year, quarters[end_date.month]
    if (start_year == end_year) and (start_qtr == end_qtr):
        return [(start_year, start_qtr)]
    out_qtrs = []
    for _year in range(start_year, end_year+1):
        if start_year == end_year:
            _qtrs = range(start_qtr, end_qtr+1)
        elif _year == start_year:
            _qtrs = range(start_qtr, 5)
        elif _year == end_year:
            _qtrs = range(1, end_qtr+1)
        for _qtr in _qtrs:
            out_qtrs.append((_year, _qtr))
    return out_qtrs

def get_start_end_fiscal_period(year, quarter):
    end_mth = quarter*3
    start_mth = end_mth-2
    start = datetime.date(year, start_mth, 1)
    end = datetime.date(year, end_mth, 28)
    return start, end

def get_forward_spend_item(ele, activity, iati_identifier, exchange_rates, 
                           forward_spend_type_code):
    # Collect data
    _start_date = ele.xpath("period-start/@iso-date")
    start_date = util.make_date_from_iso(_start_date[0])
    _end_date = ele.xpath("period-end/@iso-date")
    if _end_date:
        end_date = util.make_date_from_iso(_end_date[0])
    else:
        end_date = start_date
    value = getfirst(ele.xpath("value/text()"))
    _value_date = getfirst(ele.xpath("value/@value-date"))
    value_date = util.make_date_from_iso(_value_date)
    currency = get_currency(activity, ele)
    exchange_rate = exchange_rates.closest_rate(
        currency, value_date)["conversion_rate"]
    value_usd = (float(value) * exchange_rate)

    # Correct to quarters
    # If start and end months are not in the same quarter, then we need to handle this…

    fiscal_periods = get_fiscal_periods(start_date, end_date)
    # There is a budget, but the end date is before the start date. Ignore.
    if len(fiscal_periods) == 0: return []
    fiscal_period_value = value_usd/len(fiscal_periods)
    fps = []
    for year, quarter in fiscal_periods:
        fs = models.ForwardSpend()
        start_d, end_d = get_start_end_fiscal_period(year, quarter)
        fs.period_start_date = start_d
        fs.period_end_date = end_d
        fs.value = fiscal_period_value
        fs.value_currency = u"USD"
        fs.value_date = value_date
        fs.forward_spend_type_code = forward_spend_type_code
        fps.append(fs)
    return fps

def fs_overlaps(fs, forward_spends):
    fs_start_date = fs.period_start_date
    fs_end_date = fs.period_end_date
    for fs_existing in forward_spends:
        if ((min(fs_existing.period_end_date, fs_end_date) - 
             max(fs_existing.period_start_date, fs_start_date)).days + 1) > 0:
            return True
    return False

def get_forward_spend(activity, iati_identifier, version, exchange_rates):
    # Consider original / revised budgets and planned disbursements as equivalent
    # Line these up alongside each other and take only one.
    forward_spends = []
    for ele in activity.xpath("./budget[@type='1']|budget[not(@type)]"):
        fs = get_forward_spend_item(ele, activity, iati_identifier, 
            exchange_rates, 1)
        forward_spends += fs
    return forward_spends 
    #FIXME
    for ele in activity.xpath("./budget[@type='2']"):
        fs = get_forward_spend_item(ele, activity, iati_identifier, 
            exchange_rates, 2)
        for fs_item in fs:
            if not fs_overlaps(fs_item, forward_spends):
                forward_spends.append(fs_item)
    return forward_spends 

def get_transactions(activity, iati_identifier, version, exchange_rates):
    ret = []
    for ele in activity.xpath("./transaction"):
        currency = get_currency(activity, ele)
        t_type = unicode(getfirst(ele.xpath("transaction-type/@code")))
        if version == 2:
            t_type = get_t_type(t_type)
        t_date = getfirst(ele.xpath("transaction-date/@iso-date"))
        t_value = getfirst(ele.xpath("value/text()"))
        t_value_date = getfirst(ele.xpath("value/@value-date"))
        
        exchange_rate = exchange_rates.closest_rate(
            currency, util.make_date_from_iso(t_value_date))["conversion_rate"]

        if not (t_type and t_date and t_value and t_value_date): 
            print "woah, transaction doesn't look right"
            print "Extending org is", activity.xpath("participating-org[@role='Extending']/@ref")
            print "t_type is", t_type
            print "t_date is", t_date
            print "t_value is", t_value
            print "t_value_date is", t_value_date
            continue

        tr = models.Transaction()
        tr.value = (float(t_value) * exchange_rate)
        tr.value_date = datetime.datetime.strptime(
                t_value_date, "%Y-%m-%d" )
        tr.value_currency = u"USD"
        tr.transaction_date = datetime.datetime.strptime(
                t_date, "%Y-%m-%d" )
        tr.transaction_type_code = t_type
        tr.finance_type_code =  avoidIntegrityError(
                get_alt(ele.xpath("finance-type/@code"),
                activity.xpath('default-finance-type/@code')),
                "FinanceType", "110")
        ret.append(tr)
    return ret 

def get_titles(activity, version):
    ret = []
    loop = {1: activity.xpath("./title"),
            2: activity.xpath("./title/narrative")}[version]
    for ele in loop:
        title = models.Title()
        title.text = unicode(ele.text)
        title.lang = unicode(getfirst(ele.xpath('@xml:lang'),
                             getfirst(activity.xpath('@xml:lang'))))
        ret.append(title)
    return ret

def get_document_titles(title_field):
    tfs = []
    for field in title_field:
        document_title = models.DocumentTitle()
        document_title.title = field.text
        document_title.lang = getfirst(field.xpath("@xml:lang"))
        tfs.append(document_title)
    return tfs

def get_categories(document):
    cats = []
    loop = document.xpath("category")
    for ele in loop:
        category = models.DocumentsCategories()
        category.documentcategory_code = ele.get("code")
        cats.append(category)
    return cats

def get_documents(activity, version):
    ret = []
    loop = activity.xpath("./document-link")
    for ele in loop:
        title_field = {1: ele.xpath("./title"),
                    2: ele.xpath("./title/narrative")}[version]
        document = models.Document()
        #document.title = get_document_titles(title_field)
        #document.lang = unicode(getfirst(ele.xpath('language/@code'), "en"))
        #document.url = unicode(ele.get("url"))
        #document.format = unicode(ele.get("format"))
        #document.categories = get_categories(ele)
        ret.append(document)
    return ret

def get_descriptions(activity, version):
    ret = []
    loop = {1: activity.xpath("./description"),
            2: activity.xpath("./description/narrative")}[version]
    for ele in loop:
        description = models.Description()
        description.text = unicode(ele.text)
        description.lang = unicode(getfirst(ele.xpath('@xml:lang'),
                             getfirst(activity.xpath('@xml:lang'))))
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

def avoidIntegrityError(value, codelist, default):
    if value not in codelists.CODELISTS[codelist]:
        return default
    return value

def write_activity(activity, reporting_org_id, version, exchange_rates):
    iati_identifier = unicode(getfirst(activity.xpath('iati-identifier/text()')))
    #if this identifier already exists, then delete, otherwise, insert
    checkA = models.Activity.query.filter_by(iati_identifier=iati_identifier).first()
    if checkA:
        return
        db.session.delete(checkA)
        db.session.commit()
    a = models.Activity()
    a.iati_identifier = iati_identifier
    a.reporting_org_id = reporting_org_id
    a.last_updated = dtparse(activity.get("last-updated-datetime"))
    a.all_titles = get_titles(activity, version)
    a.recipient_countries = get_recipient_countries(activity)
    a.all_descriptions = get_descriptions(activity, version)
    a.sectors = get_sectors(activity, version)
    a.participating_orgs = get_orgs(activity, version)
    a.transactions = get_transactions(activity, a.iati_identifier, 
                                      version, exchange_rates)
    a.forward_spend = get_forward_spend(activity, a.iati_identifier, 
                                      version, exchange_rates)
    #a.documents = get_documents(activity, version)
    a.sectors = get_sectors(activity, version)
    a.status_code = unicode(null_to_default(
        getfirst(activity.xpath('activity-status/@code')),
        "2"
        ))
    a.capital_exp = null_to_default(
        getfirst(activity.xpath('capital-spend/@percentage')),
        None
        )
    a.collaboration_type_code = unicode(null_to_default(
        getfirst(activity.xpath('collaboration-type/@code')),
        "2"
        ))
    a.aid_type_code = avoidIntegrityError(
getfirst(activity.xpath('default-aid-type/@code|transaction/aid-type/@code')),
        "AidType", "C01")
    a.date_start_planned = get_date(activity, {1: 'start-planned', 2: "1"}[version])
    a.date_end_planned = get_date(activity, {1: 'end-planned', 2: "3"}[version])
    a.date_start_actual = get_date(activity, {1: 'start-actual', 2: "2"}[version])
    a.date_end_actual = get_date(activity, {1: 'end-actual', 2: "4"}[version])
    db.session.add(a)
    db.session.commit()

def get_version(activity):
    ns = activity.nsmap["iati-extra"]
    version = activity.get("{%s}version" % ns, "1.05")
    if version in ("2.01", "2.02"):
        return 2
    elif version in ("1.01", "1.04", "1.05"):
        #FIXME when looking at locations, handle differently
        return 1
    raise UnrecognisedVersionException("""The IATI-XML version {} was not 
    recognised.""".format(version))

def parse_doc(reporting_org_id, doc, update_exchange_rates=True, sample=False):
    exchange_rates = exchangerates.CurrencyConverter(update=update_exchange_rates)
    reporting_org_code = absettings.reporting_org_by_id(reporting_org_id).code
    if reporting_org_code in flatten_rules.FLATTEN_RULES:
        doc = flattener.flatten(doc.find("iati-activities"))[reporting_org_code]
    activities = doc.xpath('//iati-activity')
    print("Parsing {} activities".format(len(activities)))
    for i, activity in enumerate(activities):
        version = get_version(activity)
        try:
            write_activity(activity, reporting_org_id,
                       version, exchange_rates)
        except sa.exc.IntegrityError:
            db.session.rollback()
            iati_identifier = activity.xpath("iati-identifier/text()")
            print("""Unable to parse activity {} as one or more codes used
            are invalid""".format("".join(iati_identifier)))

def parse_file(filename, sample=False):
    doc=etree.parse(filename)
    parse_doc(doc)
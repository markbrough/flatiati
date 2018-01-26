# -*- coding: utf-8 -*-
import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from flask.ext.babel import get_locale
import functools as ft
from abmapper import db

country_relationship = ft.partial(
    sa.orm.relationship,
    cascade="all,delete",
    passive_deletes=True,
    backref="recipientcountry"
)
act_relationship = ft.partial(
    sa.orm.relationship,
    cascade="all,delete",
    passive_deletes=True,
    backref="activity"
)
other_relationship = ft.partial(
    sa.orm.relationship,
    cascade="all,delete",
    passive_deletes=True
)
lazy_act_relationship = ft.partial(
    sa.orm.relationship,
    cascade="all,delete",
    lazy='dynamic',
    passive_deletes=True,
)
act_ForeignKey = ft.partial(
    sa.ForeignKey,
    ondelete="CASCADE"
)
FWDDATA_QUERY = """
    SELECT sum(value) AS value,
    strftime('%%Y', DATE(period_start_date, 'start of month', '-%s month'))
    AS fiscal_year
    FROM forwardspend
    WHERE forwardspend.activity_iati_identifier = '%s'
    AND value > 0
    GROUP BY fiscal_year
    ORDER BY forwardspend.period_start_date DESC
    """

FYDATA_QUERY = """
    SELECT sum(value) AS value,
    strftime('%%Y', DATE(transaction_date, 'start of month', '-%s month'))
    AS fiscal_year,
    CASE 
        WHEN strftime('%%m', DATE(transaction_date, 'start of month', '-%s month')) IN ('01','02','03') THEN 'Q1'
        WHEN strftime('%%m', DATE(transaction_date, 'start of month', '-%s month')) IN ('04','05','06') THEN 'Q2'
        WHEN strftime('%%m', DATE(transaction_date, 'start of month', '-%s month')) IN ('07','08','09') THEN 'Q3'
        WHEN strftime('%%m', DATE(transaction_date, 'start of month', '-%s month')) IN ('10','11','12') THEN 'Q4'
    END AS fiscal_quarter
    FROM atransaction
    WHERE atransaction.activity_iati_identifier = '%s'
    AND atransaction.transaction_type_code IN ('%s')
    GROUP BY fiscal_quarter, fiscal_year
    ORDER BY atransaction.transaction_date DESC
    """

# The "Unique Object" pattern
# http://www.sqlalchemy.org/trac/wiki/UsageRecipes/UniqueObject
def _unique(session, cls, hashfunc, queryfunc, constructor, arg, kw):
    cache = getattr(session, '_unique_cache', None)
    if cache is None:
        session._unique_cache = cache = {}

    key = (cls, hashfunc(*arg, **kw))
    if key in cache:
        return cache[key]
    else:
        with session.no_autoflush:
            q = session.query(cls)
            q = queryfunc(q, *arg, **kw)
            obj = q.first()
            if not obj:
                obj = constructor(*arg, **kw)
                session.add(obj)
        cache[key] = obj
        return obj


class UniqueMixin(object):
    @classmethod
    def unique_hash(cls, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def unique_filter(cls, query, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def as_unique(cls, session, *arg, **kw):
        return _unique(
            session,
            cls,
            cls.unique_hash,
            cls.unique_filter,
            cls,
            arg, kw
        )

def none_is_zero(value):
    if value == None:
        return 0
    return value

class Activity(db.Model):
    __tablename__ = 'activity'
    iati_identifier = sa.Column(sa.UnicodeText, primary_key=True)
    activity_lang = sa.Column(sa.UnicodeText)
    default_currency = sa.Column(sa.UnicodeText)
    hierarchy = sa.Column(sa.UnicodeText)
    last_updated = sa.Column(sa.DateTime)
    reporting_org_id = sa.Column(
        act_ForeignKey("reportingorg.id"),
        nullable=False,
        index=True)
    reporting_org = sa.orm.relationship("ReportingOrg")
    funding_org = sa.Column(sa.UnicodeText)
    funding_org_ref = sa.Column(sa.UnicodeText)
    funding_org_type = sa.Column(sa.UnicodeText)
    extending_org = sa.Column(sa.UnicodeText)
    extending_org_ref = sa.Column(sa.UnicodeText)
    extending_org_type = sa.Column(sa.UnicodeText)
    implementing_org = sa.Column(sa.UnicodeText)
    implementing_org_ref = sa.Column(sa.UnicodeText)
    implementing_org_type = sa.Column(sa.UnicodeText)

    recipient_countries = act_relationship("RecipientCountries")

    flow_type = sa.Column(sa.UnicodeText)
    flow_type_code = sa.Column(sa.UnicodeText)

    aid_type = sa.orm.relationship("AidType")
    aid_type_code = sa.Column(
        act_ForeignKey("aidtype.code"),
        nullable=False,
        index=True)

    all_titles = act_relationship("Title")
    all_descriptions = act_relationship("Description")

    date_start_actual = sa.Column(sa.Date)
    date_start_planned = sa.Column(sa.Date)
    date_end_actual = sa.Column(sa.Date)
    date_end_planned = sa.Column(sa.Date)

    status_code = sa.Column(
        act_ForeignKey("activitystatus.code"),
        nullable=False,
        index=True)
    status = sa.orm.relationship("ActivityStatus")

    collaboration_type_code = sa.Column(
        act_ForeignKey("collaborationtype.code"),
        nullable=False,
        index=True)
    collaboration_type = sa.orm.relationship("CollaborationType")

    contact_organisation = sa.Column(sa.UnicodeText)
    contact_telephone = sa.Column(sa.UnicodeText)
    contact_email = sa.Column(sa.UnicodeText)
    contact_mailing_address = sa.Column(sa.UnicodeText)

    tied_status = sa.Column(sa.UnicodeText)
    tied_status_code = sa.Column(sa.UnicodeText)

    activity_website = sa.Column(sa.UnicodeText)

    sectors = act_relationship("Sector")

    participating_orgs = act_relationship("Participation")

    transactions = act_relationship("Transaction")

    forward_spend = act_relationship("ForwardSpend")

    capital_exp = sa.Column(sa.Float(precision=2))

    #documents = act_relationship("Document")

    @hybrid_property
    def total_commitments(self):
        return db.engine.execute(sa.select([sa.func.sum(Transaction.value)]).\
                where(Transaction.activity_iati_identifier==self.iati_identifier).\
                where(sa.or_(Transaction.transaction_type_code=="C", 
                    Transaction.transaction_type_code=="IC"))).first()[0]

    @hybrid_property
    def total_disbursements(self):
        return db.engine.execute(sa.select([sa.func.sum(Transaction.value)]).\
                where(Transaction.activity_iati_identifier==self.iati_identifier).\
                where(sa.or_(Transaction.transaction_type_code=="D",
                    Transaction.transaction_type_code=="E"))).first()[0]

    @hybrid_property
    def implementing_orgs(self):
        def filter_implementing(orgs):
            return orgs.role == "Implementing"
        return filter(filter_implementing, self.participating_orgs)

    @hybrid_property
    def titles(self):
        def filter_titles(title):
            return title.lang == str(get_locale())
        relevant_titles = filter(filter_titles, self.all_titles)
        if not relevant_titles:
            return self.all_titles
        return relevant_titles

    @hybrid_property
    def country_pcts(self):
        countries = self.recipient_countries
        return dict(map(lambda c: (c.recipient_country_code, 
                                   "{0:.2f}".format(c.percentage)), 
                       countries))

    @hybrid_property
    def country_pcts_float(self):
        countries = self.recipient_countries
        return dict(map(lambda c: (c.recipient_country_code, 
                                   c.percentage), 
                       countries))

    @hybrid_property
    def descriptions(self):
        def filter_descriptions(description):
            return description.lang == str(get_locale())
        relevant_descriptions = filter(filter_descriptions,
                                       self.all_descriptions)
        if not relevant_descriptions:
            return self.all_descriptions
        return relevant_descriptions

    @hybrid_method
    def FY_forward_spend_dict(self, recipient_country):
        fydata = db.engine.execute(FWDDATA_QUERY % 
                        (recipient_country.fiscalyear_modifier,
                         self.iati_identifier)
                                  ).fetchall()
        return {
                    "{}".format(fyval.fiscal_year): {
                    "fiscal_year": fyval.fiscal_year,
                    "value": round(fyval.value, 2)
                    }
                    for fyval in fydata
                }

    @hybrid_method
    def FY_disbursements_dict(self, recipient_country):
        fydata = db.engine.execute(FYDATA_QUERY % 
                        (recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         self.iati_identifier, "D','E")
                                  ).fetchall()
        return {
                    "{} {}".format(fyval.fiscal_year, fyval.fiscal_quarter): {
                    "fiscal_year": fyval.fiscal_year,
                    "fiscal_quarter": fyval.fiscal_quarter,
                    "value": round(fyval.value, 2)
                    }
                    for fyval in fydata
                }

    @hybrid_method
    def FY_commitments_dict(self, recipient_country):
        fydata = db.engine.execute(FYDATA_QUERY % 
                        (recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         self.iati_identifier, "C','IC")
                                  ).fetchall()
        return {
                    "{} {}".format(fyval.fiscal_year, fyval.fiscal_quarter): {
                    "fiscal_year": fyval.fiscal_year,
                    "fiscal_quarter": fyval.fiscal_quarter,
                    "value": fyval.value
                    }
                    for fyval in fydata
                }
    @hybrid_method
    def FY_disbursements(self, recipient_country):
        country_pct = self.country_pcts_float[recipient_country.code]
        fydata = db.engine.execute(FYDATA_QUERY % 
                        (recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         self.iati_identifier, "D','E")
                                  ).fetchall()
        return [{
                    "fiscal_year": fyval.fiscal_year,
                    "fiscal_quarter": fyval.fiscal_quarter,
                    "value": "{:,.2f}".format(fyval.value),
                    "value_country": "{:,.2f}".format(fyval.value * country_pct/100)
                }
                for fyval in fydata]

    @hybrid_method
    def FY_commitments(self, recipient_country):
        country_pct = self.country_pcts_float[recipient_country.code]
        fydata = db.engine.execute(FYDATA_QUERY % 
                        (recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         recipient_country.fiscalyear_modifier,
                         self.iati_identifier, "C','IC")
                                  ).fetchall()
        return  [{
                    "fiscal_year": fyval.fiscal_year,
                    "fiscal_quarter": fyval.fiscal_quarter,
                    "value": "{:,.2f}".format(fyval.value),
                    "value_country": "{:,.2f}".format(fyval.value * country_pct/100)
                }
                for fyval in fydata]


    @hybrid_method
    def FY_forward_spend(self, recipient_country):
        country_pct = self.country_pcts_float[recipient_country.code]
        fydata = db.engine.execute(FWDDATA_QUERY % 
                        (recipient_country.fiscalyear_modifier,
                         self.iati_identifier)
                                  ).fetchall()
        return [{
                    "fiscal_year": fyval.fiscal_year,
                    "value": "{:,.2f}".format(fyval.value),
                    "value_country": "{:,.2f}".format(fyval.value * country_pct/100)
                }
                for fyval in fydata]

    @hybrid_property
    def finance_types(self):
        return db.session.query(FinanceType
            ).distinct(FinanceType.code
            ).join(Transaction
            ).filter(Transaction.activity_iati_identifier == self.iati_identifier
            ).filter(Transaction.activity_iati_identifier == self.iati_identifier).all()

class Title(db.Model):
    __tablename__ = 'title'
    id = sa.Column(sa.Integer, primary_key=True)   
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    text = sa.Column(sa.UnicodeText)
    lang = sa.Column(sa.UnicodeText)

    def as_string(self):
        return {c.text: getattr(self, c.text) for c in self.__table__.columns}

class Description(db.Model):
    __tablename__ = 'description'
    id = sa.Column(sa.Integer, primary_key=True)   
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    text = sa.Column(sa.UnicodeText)
    lang = sa.Column(sa.UnicodeText)

class RecipientCountry(db.Model):
    __tablename__ = 'recipientcountry'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)
    fiscalyear = sa.Column(sa.UnicodeText)
    fiscalyear_modifier = sa.Column(sa.Integer,
        nullable=False,
        default=0)
    recipient_countries = country_relationship("RecipientCountries")
    active = sa.Column(sa.Boolean, default=False)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

    @hybrid_property
    def num_activities(self):
        return Activity.query.filter(
            RecipientCountries.recipient_country_code==self.code
        ).count()

class RecipientCountries(db.Model):
    __tablename__ = 'recipientcountries'
    id = sa.Column(sa.Integer, primary_key=True)
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    percentage = sa.Column(sa.Float(precision=2))
    recipient_country = sa.orm.relationship("RecipientCountry")
    recipient_country_code = sa.Column(
        act_ForeignKey("recipientcountry.code"),
        nullable=False,
        index=True)

    def as_string(self):
        return {c.text: getattr(self, c.text) for c in self.__table__.columns}

class ActivityStatus(db.Model):
    __tablename__ = 'activitystatus'
    code = sa.Column(sa.Integer, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

class CollaborationType(db.Model):
    __tablename__ = 'collaborationtype'
    code = sa.Column(sa.Integer, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

class FinanceType(db.Model):
    __tablename__ = 'financetype'
    code = sa.Column(sa.Integer, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

class AidType(db.Model):
    __tablename__ = 'aidtype'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

class ReportingOrg(db.Model):
    __tablename__ = 'reportingorg'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.UnicodeText)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)
    active = sa.Column(sa.Boolean, default=False)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

    @hybrid_property
    def num_activities(self):
        return Activity.query.filter_by(
            reporting_org_id=self.id
        ).count()

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Transaction(db.Model):
    __tablename__ = 'atransaction'
    id = sa.Column(sa.Integer, primary_key=True)
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    value = sa.Column(sa.Float(precision=2))
    value_date = sa.Column(sa.Date)
    value_currency = sa.Column(sa.UnicodeText)
    transaction_date = sa.Column(sa.Date)
    transaction_type_code = sa.Column(sa.UnicodeText)
    finance_type_code = sa.Column(
        act_ForeignKey("financetype.code"))
    finance_type = sa.orm.relationship("FinanceType")

class ForwardSpend(db.Model):
    __tablename__ = 'forwardspend'
    id = sa.Column(sa.Integer, primary_key=True)
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    value = sa.Column(sa.Float(precision=2))
    value_date = sa.Column(sa.Date)
    value_currency = sa.Column(sa.UnicodeText)
    period_start_date = sa.Column(sa.Date)
    period_end_date = sa.Column(sa.Date)
    forwardspendtype_code = sa.Column(
        act_ForeignKey("forwardspendtype.code"))
    forward_spend_type = sa.orm.relationship("ForwardSpendType")

class ForwardSpendType(db.Model):
    __tablename__ = 'forwardspendtype'
    code = sa.Column(sa.Integer, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

# Put everything into sectors table, and link back to specific activity. 
# Might want to normalise this in future.

class Sector(db.Model):
    __tablename__ = 'sector'
    id = sa.Column(sa.Integer, primary_key=True)   
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    code = sa.Column(
        act_ForeignKey("dacsector.code"),
        nullable=True)
    percentage = sa.Column(sa.Float(precision=2))
    edited = sa.Column(sa.Boolean, default=False)
    deleted = sa.Column(sa.Boolean, default=False)
    assumed = sa.Column(sa.Boolean, default=False)
    dacsector = sa.orm.relationship("DACSector")

# Code and name should be from DACSectors table
# DACSectors table should relate to commoncode table

class DACSector(db.Model):
    __tablename__ = 'dacsector'
    code = sa.Column(sa.Integer, primary_key=True)
    dac_sector_code = sa.Column(sa.Integer)
    dac_sector_name_EN = sa.Column(sa.UnicodeText)
    dac_sector_name_FR = sa.Column(sa.UnicodeText)
    dac_five_code = sa.Column(sa.Integer)
    dac_five_name_EN = sa.Column(sa.UnicodeText)
    dac_five_name_FR = sa.Column(sa.UnicodeText)
    description_EN = sa.Column(sa.UnicodeText)
    description_FR = sa.Column(sa.UnicodeText)
    notes_EN = sa.Column(sa.UnicodeText)
    notes_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def dac_sector_name(self):
        if str(get_locale()) == "fr":
            return self.dac_sector_name_FR
        return self.dac_sector_name_EN

    @hybrid_property
    def dac_five_name(self):
        if str(get_locale()) == "fr":
            return self.dac_five_name_FR
        return self.dac_five_name_EN

    @hybrid_property
    def description(self):
        if str(get_locale()) == "fr":
            return self.description_FR
        return self.description_EN

    @hybrid_property
    def notes(self):
        if str(get_locale()) == "fr":
            return self.notes_FR
        return self.notes_EN

class BudgetMapping(db.Model):
    __tablename__ = 'budgetmapping'
    id = sa.Column(sa.Integer, primary_key=True)
    order = sa.Column(sa.Integer)
    name = sa.Column(sa.UnicodeText)
    recipientcountry_code = sa.Column(
        act_ForeignKey("recipientcountry.code"),
        nullable=False,
        index=True)
    is_constant = sa.Column(sa.Boolean,
                        default=False)
    constant_value = sa.Column(sa.UnicodeText,
                        nullable=True)
    maps_to = sa.Column(sa.Integer)
    budgetmappingdac = other_relationship("BudgetMappingDACCode")
    budgetmappingro = other_relationship("BudgetMappingRO")

class BudgetMappingDACCode(db.Model):
    __tablename__ = 'budgetmappingdac'
    id = sa.Column(sa.Integer, primary_key=True)
    budgetmapping_id = sa.Column(
        act_ForeignKey("budgetmapping.id"),
        nullable=False,
        index=True)
    dacsector_code = sa.Column(
        act_ForeignKey("dacsector.code"),
        nullable=False,
        index=True)
    code = sa.Column(sa.UnicodeText)
    name = sa.Column(sa.UnicodeText)

class BudgetMappingRO(db.Model):
    __tablename__ = 'budgetmappingro'
    id = sa.Column(sa.Integer, primary_key=True)
    budgetmapping_id = sa.Column(
        act_ForeignKey("budgetmapping.id"),
        nullable=False,
        index=True)
    reportingorg_id = sa.Column(
        act_ForeignKey("reportingorg.id"),
        nullable=False,
        index=True)
    aidtype_code = sa.Column(
        act_ForeignKey("aidtype.code"),
        nullable=True,
        index=True)
    financetype_code = sa.Column(
        act_ForeignKey("financetype.code"),
        nullable=True,
        index=True)
    code = sa.Column(sa.UnicodeText)
    name = sa.Column(sa.UnicodeText)

class RelatedActivity(db.Model):
    __tablename__ = 'relatedactivity'
    id = sa.Column(sa.Integer, primary_key=True)
    activity_iati_identifier = sa.Column(sa.UnicodeText, index=True)
    reltext = sa.Column(sa.UnicodeText)
    relref = sa.Column(sa.UnicodeText)
    reltype = sa.Column(sa.UnicodeText)

class Participation(db.Model):
    __tablename__ = "participation"
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        primary_key=True)
    organisation_id = sa.Column(
        sa.ForeignKey("organisation.id"),
        primary_key=True)
    role = sa.Column(
        sa.UnicodeText,
        primary_key=True)
    organisation = sa.orm.relationship("Organisation")

class Organisation(db.Model, UniqueMixin):
    __tablename__ = "organisation"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    ref = sa.Column(sa.Unicode, nullable=False)
    name = sa.Column(sa.Unicode, default=u"", nullable=True)
    type = sa.Column(sa.Unicode, default=u"", nullable=True)
    __table_args__ = (sa.UniqueConstraint('ref', 'name', 'type'),)
    @classmethod
    def unique_hash(cls, ref, name, type, **kw):
        return ref, name, type
    @classmethod
    def unique_filter(cls, query, ref, name, type, **kw):
        return query.filter(
            (cls.ref == ref) & (cls.name == name)
        )
    def __repr__(self):
        return "Organisation(ref=%r)" % self.ref
    def __unicode__(self):
        return u"Organisation ref='%s'" % self.ref
"""
class Document(db.Model):
    __tablename__ = 'document'
    id = sa.Column(sa.Integer, primary_key=True)
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        primary_key=True)
    url = sa.Column(sa.UnicodeText)
    format = sa.Column(sa.UnicodeText)
    lang = sa.Column(sa.UnicodeText)
    #title = other_relationship("DocumentTitle")
    #document_categories = other_relationship("DocumentsCategories")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class DocumentTitle(db.Model):
    __tablename__ = 'documenttitle'
    id = sa.Column(sa.Integer, primary_key=True)
    document_id = sa.Column(
        act_ForeignKey("document.id"),
        primary_key=True)
    title = sa.Column(sa.UnicodeText)
    lang = sa.Column(sa.UnicodeText)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class DocumentCategory(db.Model):
    __tablename__ = 'documentcategory'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    name_EN = sa.Column(sa.UnicodeText)
    name_FR = sa.Column(sa.UnicodeText)
    activity_doc = sa.Column(sa.Boolean, default=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class DocumentsCategories(db.Model):
    __tablename__ = 'documentscategories'
    id = sa.Column(sa.Integer, primary_key=True)
    document_id = sa.Column(
        act_ForeignKey("document.id"),
        primary_key=True)
    documentcategory_code = sa.Column(
        act_ForeignKey("documentcategory.code"),
        primary_key=True)
    documentcategory = sa.orm.relationship("DocumentCategory")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
"""
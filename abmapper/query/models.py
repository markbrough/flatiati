# -*- coding: utf-8 -*-
import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property
from flask.ext.babel import get_locale
import functools as ft
from abmapper import db

act_relationship = ft.partial(
    sa.orm.relationship,
    cascade="all,delete",
    passive_deletes=True,
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

FYDATA_QUERY = """
    SELECT sum(value) AS value,
    strftime('%%Y', DATE(transaction_date, '-%s month'))
    AS fiscal_year
    FROM atransaction
    WHERE atransaction.activity_iati_identifier = '%s'
    AND atransaction.transaction_type_code = '%s'
    GROUP BY fiscal_year
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
    id = sa.Column(sa.Integer, primary_key=True)
    activity_lang = sa.Column(sa.UnicodeText)
    default_currency = sa.Column(sa.UnicodeText)
    hierarchy = sa.Column(sa.UnicodeText)
    last_updated = sa.Column(sa.UnicodeText)
    reporting_org_ref = sa.Column(sa.UnicodeText)

    funding_org = sa.Column(sa.UnicodeText)
    funding_org_ref = sa.Column(sa.UnicodeText)
    funding_org_type = sa.Column(sa.UnicodeText)
    extending_org = sa.Column(sa.UnicodeText)
    extending_org_ref = sa.Column(sa.UnicodeText)
    extending_org_type = sa.Column(sa.UnicodeText)
    implementing_org = sa.Column(sa.UnicodeText)
    implementing_org_ref = sa.Column(sa.UnicodeText)
    implementing_org_type = sa.Column(sa.UnicodeText)

    recipient_region = sa.Column(sa.UnicodeText)
    recipient_region_code = sa.Column(sa.UnicodeText)

    recipient_country = sa.orm.relationship("RecipientCountry")
    recipient_country_code = sa.Column(
        act_ForeignKey("recipientcountry.code"),
        nullable=False,
        index=True)

    collaboration_type = sa.Column(sa.UnicodeText)
    collaboration_type_code = sa.Column(sa.UnicodeText)
    flow_type = sa.Column(sa.UnicodeText)
    flow_type_code = sa.Column(sa.UnicodeText)

    aid_type = sa.orm.relationship("AidType")
    aid_type_code = sa.Column(
        act_ForeignKey("aidtype.code"),
        nullable=False,
        index=True)

    finance_type = sa.Column(sa.UnicodeText)
    finance_type_code = sa.Column(sa.UnicodeText)

    iati_identifier = sa.Column(sa.UnicodeText, index=True)

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

    capital_exp = sa.Column(sa.Float(precision=2),
        default=0.00)

    @hybrid_property
    def total_commitments(self):
        return db.engine.execute(sa.select([sa.func.sum(Transaction.value)]).\
                where(Transaction.activity_iati_identifier==self.iati_identifier).\
                where(Transaction.transaction_type_code=="C")).first()[0]

    @hybrid_property
    def total_disbursements(self):
        return db.engine.execute(sa.select([sa.func.sum(Transaction.value)]).\
                where(Transaction.activity_iati_identifier==self.iati_identifier).\
                where(Transaction.transaction_type_code=="D")).first()[0]

    pct_mappable_before_sql = """
        SELECT sum(sector.percentage) AS sum_1
        FROM sector
        JOIN dacsector ON dacsector.code = sector.code
        JOIN commoncode ON commoncode.id = dacsector.cc_id
        JOIN ccbudgetcode ON ccbudgetcode.cc_id = commoncode.id
        JOIN budgetcode ON budgetcode.id = ccbudgetcode.budgetcode_id
        WHERE sector.activity_iati_identifier = '%s'
        AND sector.edited = 0 AND dacsector.cc_id != "0"
        AND budgetcode.country_code="%s"
        AND budgetcode.budgettype_code="%s";
        """

    pct_mappable_after_sql = """
        SELECT sum(sector.percentage) AS sum_1
        FROM sector
        JOIN dacsector ON dacsector.code = sector.code
        JOIN commoncode ON commoncode.id = dacsector.cc_id
        JOIN ccbudgetcode ON ccbudgetcode.cc_id = commoncode.id
        JOIN budgetcode ON budgetcode.id = ccbudgetcode.budgetcode_id
        WHERE sector.activity_iati_identifier = '%s'
        AND sector.deleted = 0 AND dacsector.cc_id != "0"
        AND budgetcode.country_code="%s"
        AND budgetcode.budgettype_code="%s";
        """

    @hybrid_property
    def pct_mappable_before(self):
        return none_is_zero(db.engine.execute(
            self.pct_mappable_before_sql % (self.iati_identifier,
                   self.recipient_country_code,
                   "f")).first()[0])

    @hybrid_property
    def pct_mappable_after(self):
        return none_is_zero(db.engine.execute(
            self.pct_mappable_after_sql % (self.iati_identifier,
                   self.recipient_country_code,
                   "f")).first()[0])

    @hybrid_property
    def pct_mappable_before_admin(self):
        return none_is_zero(db.engine.execute(
             self.pct_mappable_before_sql % (self.iati_identifier,
                   self.recipient_country_code,
                   "a")).first()[0])

    @hybrid_property
    def pct_mappable_after_admin(self):
        return none_is_zero(db.engine.execute(
            self.pct_mappable_after_sql % (self.iati_identifier,
                   self.recipient_country_code,
                   "a")).first()[0])

    @hybrid_property
    def pct_mappable_diff(self):
        try:
            return "{0:.2f}".format(self.pct_mappable_after - self.pct_mappable_before)
        except TypeError:
            return 0

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
    def descriptions(self):
        def filter_descriptions(description):
            return description.lang == str(get_locale())
        relevant_descriptions = filter(filter_descriptions,
                                       self.all_descriptions)
        if not relevant_descriptions:
            return self.all_descriptions
        return relevant_descriptions

    @hybrid_property
    def FY_disbursements(self):
        fydata = db.engine.execute(FYDATA_QUERY % 
                        (self.recipient_country.fiscalyear_modifier,
                         self.iati_identifier, "D")
                                  ).fetchall()
        return {
                    fyval.fiscal_year: {
                    "fiscal_year": fyval.fiscal_year,
                    "value": fyval.value
                    }
                    for fyval in fydata
                }

    @hybrid_property
    def FY_commitments(self):
        fydata = db.engine.execute(FYDATA_QUERY % 
                        (self.recipient_country.fiscalyear_modifier,
                         self.iati_identifier, "C")
                                  ).fetchall()
        return {
                    fyval.fiscal_year: {
                    "fiscal_year": fyval.fiscal_year,
                    "value": fyval.value
                    }
                    for fyval in fydata
                }

class Title(db.Model):
    __tablename__ = 'title'
    id = sa.Column(sa.Integer, primary_key=True)   
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    text = sa.Column(sa.UnicodeText)
    lang = sa.Column(sa.UnicodeText)
    percentage = sa.Column(sa.Integer)
    activity = sa.orm.relationship("Activity")

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

class RecipientCountry(db.Model):
    __tablename__ = 'recipientcountry'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)
    fiscalyear = sa.Column(sa.UnicodeText)
    fiscalyear_modifier = sa.Column(sa.Integer,
        nullable=False,
        default=0)
    budgettype_id = sa.Column(
        act_ForeignKey("budgettype.code"),
        default=None)
    budgettype = sa.orm.relationship("BudgetType")

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

class BudgetType(db.Model):
    __tablename__ = 'budgettype'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text_EN = sa.Column(sa.UnicodeText)
    text_FR = sa.Column(sa.UnicodeText)

    @hybrid_property
    def text(self):
        if str(get_locale()) == "fr":
            return self.text_FR
        return self.text_EN

class Description(db.Model):
    __tablename__ = 'description'
    id = sa.Column(sa.Integer, primary_key=True)   
    activity_iati_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        nullable=False,
        index=True)
    text = sa.Column(sa.UnicodeText)
    lang = sa.Column(sa.UnicodeText)
    activity = sa.orm.relationship("Activity")

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
    activity = sa.orm.relationship("Activity")
    dacsector = sa.orm.relationship("DACSector")
    formersector_id = sa.Column(
        act_ForeignKey("sector.code"),
        nullable=True)

    @hybrid_property
    def formersector(self):
        return db.engine.execute("""
            SELECT sector.code AS "sector.code", 
                   sector.percentage AS "sector.percentage",
                   sector.assumed AS "sector.assumed",
                   dacsector.description_%s AS "dacsector.description"
            FROM sector
            JOIN dacsector ON sector.code = dacsector.code
            WHERE sector.id = '%s';
            """ % (str(get_locale()).upper(),
                   self.formersector_id)).first()

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
    parent_code = sa.Column(
        act_ForeignKey("dacsector.code"),
        nullable=True)
    cc_id = sa.Column(
        act_ForeignKey("commoncode.id"),
        nullable=False)
    cc = sa.orm.relationship("CommonCode")

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

class CommonCode(db.Model):
    __tablename__ = 'commoncode'
    id = sa.Column(sa.UnicodeText, primary_key=True)
    category_EN = sa.Column(sa.UnicodeText)
    sector_EN = sa.Column(sa.UnicodeText)
    function_EN = sa.Column(sa.UnicodeText)
    category_FR = sa.Column(sa.UnicodeText)
    sector_FR = sa.Column(sa.UnicodeText)
    function_FR = sa.Column(sa.UnicodeText)
    cc_budgetcode = act_relationship("CCBudgetCode")
    cc_lowerbudgetcode = act_relationship("CCLowerBudgetCode")

    @hybrid_property
    def category(self):
        if str(get_locale()) == "fr":
            return self.category_FR
        return self.category_EN

    @hybrid_property
    def sector(self):
        if str(get_locale()) == "fr":
            return self.sector_FR
        return self.sector_EN

    @hybrid_property
    def function(self):
        if str(get_locale()) == "fr":
            return self.function_FR
        return self.function_EN

class BudgetCode(db.Model):
    __tablename__ = 'budgetcode'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.UnicodeText)
    name = sa.Column(sa.UnicodeText)
    country_code = sa.Column(sa.UnicodeText, sa.ForeignKey("recipientcountry.code"))
    country = sa.orm.relationship("RecipientCountry",
                primaryjoin=country_code == RecipientCountry.code,
                foreign_keys=[country_code],
                )
    budgettype_code = sa.Column(sa.UnicodeText, sa.ForeignKey("budgettype.code"))
    budgettype = sa.orm.relationship("BudgetType",
                primaryjoin=budgettype_code == BudgetType.code,
                foreign_keys=[budgettype_code],
                )

class LowerBudgetCode(db.Model):
    __tablename__ = 'lowerbudgetcode'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.UnicodeText)
    name = sa.Column(sa.UnicodeText)
    country_code = sa.Column(sa.UnicodeText, sa.ForeignKey("recipientcountry.code"))
    country = sa.orm.relationship("RecipientCountry",
                primaryjoin=country_code == RecipientCountry.code,
                foreign_keys=[country_code],
                )
    budgettype_code = sa.Column(sa.UnicodeText, sa.ForeignKey("budgettype.code"))
    budgettype = sa.orm.relationship("BudgetType",
                primaryjoin=budgettype_code == BudgetType.code,
                foreign_keys=[budgettype_code],
                )
    parent_budgetcode_id = sa.Column(sa.Integer, sa.ForeignKey("budgetcode.id"))
    parent_budgetcode = sa.orm.relationship("BudgetCode")

class CCBudgetCode(db.Model):
    __tablename__ = 'ccbudgetcode'
    id = sa.Column(sa.Integer, primary_key=True)
    cc_id = sa.Column(sa.UnicodeText, sa.ForeignKey("commoncode.id"))
    cc = sa.orm.relationship("CommonCode")
    budgetcode_id = sa.Column(sa.Integer, sa.ForeignKey("budgetcode.id"))
    budgetcode = sa.orm.relationship("BudgetCode")

class CCLowerBudgetCode(db.Model):
    __tablename__ = 'cclowerbudgetcode'
    id = sa.Column(sa.Integer, primary_key=True)
    cc_id = sa.Column(sa.UnicodeText, sa.ForeignKey("commoncode.id"))
    cc = sa.orm.relationship("CommonCode")
    lowerbudgetcode_id = sa.Column(sa.Integer, sa.ForeignKey("lowerbudgetcode.id"))
    lowerbudgetcode = sa.orm.relationship("LowerBudgetCode")

class RelatedActivity(db.Model):
    __tablename__ = 'relatedactivity'
    id = sa.Column(sa.Integer, primary_key=True)
    activity_id = sa.Column(sa.UnicodeText, index=True)
    reltext = sa.Column(sa.UnicodeText)
    relref = sa.Column(sa.UnicodeText)
    reltype = sa.Column(sa.UnicodeText)

class Participation(db.Model):
    __tablename__ = "participation"
    activity_identifier = sa.Column(
        act_ForeignKey("activity.iati_identifier"),
        primary_key=True)
    country_code = sa.Column(
        act_ForeignKey("recipientcountry.code"),
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

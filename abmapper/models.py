import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property
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

    titles = act_relationship("Title")
    descriptions = act_relationship("Description")

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

    capital_exp = sa.Column(sa.Integer)

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
    text = sa.Column(sa.UnicodeText)

class AidType(db.Model):
    __tablename__ = 'aidtype'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text = sa.Column(sa.UnicodeText)

class RecipientCountry(db.Model):
    __tablename__ = 'recipientcountry'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text = sa.Column(sa.UnicodeText)
    budget_types = act_relationship("BudgetType")

class BudgetType(db.Model):
    __tablename__ = 'budgettypes'
    code = sa.Column(sa.UnicodeText, primary_key=True)
    text = sa.Column(sa.UnicodeText)

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
    percentage = sa.Column(sa.Integer)
    edited = sa.Column(sa.Boolean, default=False)
    deleted = sa.Column(sa.Boolean, default=False)
    activity = sa.orm.relationship("Activity")
    dacsector = sa.orm.relationship("DACSector")

# Code and name should be from DACSectors table
# DACSectors table should relate to commoncode table

class DACSector(db.Model):
    __tablename__ = 'dacsector'
    code = sa.Column(sa.Integer, primary_key=True)
    dac_sector_code = sa.Column(sa.Integer)
    dac_sector_name = sa.Column(sa.UnicodeText)
    dac_five_code = sa.Column(sa.Integer)
    dac_five_name = sa.Column(sa.UnicodeText)
    description = sa.Column(sa.UnicodeText)
    notes = sa.Column(sa.UnicodeText)
    parent_code = sa.Column(
        act_ForeignKey("dacsector.code"),
        nullable=True)
    cc_id = sa.Column(
        act_ForeignKey("commoncode.id"),
        nullable=False)
    cc = sa.orm.relationship("CommonCode")

class CommonCode(db.Model):
    __tablename__ = 'commoncode'
    id = sa.Column(sa.UnicodeText, primary_key=True)
    category = sa.Column(sa.UnicodeText)
    sector = sa.Column(sa.UnicodeText)
    function = sa.Column(sa.UnicodeText)

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

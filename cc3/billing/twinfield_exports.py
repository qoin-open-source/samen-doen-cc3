from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import os

from cc3.excelexport.utils import generate_csv, generate_xls

from .common import load_dynamic_settings

LOG = logging.getLogger(__name__)


# TODO: settings / in db
DEFAULT_TERMS_DAYS = 14
BILLING_INVOICE_CC_EMAILS = (
    'verenigingmiddelenbeheer@qoin.org',
    'community.manager@samen-doen.nl'
)


def products_list_for_export(queryset, include_headings=True):
    """Generate the list of rows for the Products csv

    queryset - Products to include

    Fields:
        Code
        Name
        Discount
        Adjust price
        Adjust VAT
        VAT code
        Unit name (single)
        Unit name (plural)
        Decimals
        Sub article
        Sub article name
        GL account
        Cost centre
        Unit price (VAT excluded)
        Units
        Unit price (VAT included)
    """
    products = []
    headings = [
        'Code',
        'Name',
        'Discount',
        'Adjust price',
        'Adjust VAT',
        'VAT code',
        'Unit name (single)',
        'Unit name (plural)',
        'Decimals',
        'Sub article',
        'Sub article name',
        'GL account',
        'Cost centre',
        'Unit price (VAT excluded)',
        'Units',
        'Unit price (VAT included)',
    ]
    dyn_settings = load_dynamic_settings()

    if include_headings:
        products.append(headings)

    for product in queryset:
        # It's mandatory to supply a unit price here, even though there
        # isn't necessarily a single unit price for the whole month.
        # Hopefully we can override in the invoices file (?)
        unit_price_ex_vat = product.get_todays_unit_price()
        products.append([
            product.article_code,  # 'Code',
            product.name,  # 'Name',
            (1 if product.is_discountable else 0),  # 'Discount',
            1,  # 'Adjust price',  #  1 if variable price
            0,  # 'Adjust VAT',
            product.tax_regime.twinfield_code,  # 'VAT code',
            '',  # 'Unit name (single)',
            '',  # 'Unit name (plural)',
            0,  # 'Decimals',
            product.subarticle_code,  # 'Sub article',
            product.subname,  # 'Sub article name',
            dyn_settings.TWINFIELD_GL_ACCOUNT_PRODUCTS,  # 'GL account',
            product.cost_centre,  # 'Cost centre',
            unit_price_ex_vat,  # 'Unit price (VAT excluded)',
            1,  # 'Units',
            '',  # 'Unit price (VAT included)',
        ])

    if not products:
        products = [[]]

    return products


def users_list_for_export(queryset, include_headings=True):
    """Generate the list of rows for the users csv

    queryset - CC3Profiles to include

    Fields:
        code,
        name,
        website,
        defaultaddress,
        addresstype,
        Companyname,
        Attentionof,
        addressline1,
        addressline2,
        postcode,
        City,
        country,
        telephone,
        fax,
        VATno,
        CoRegno,
        emailaddress,
        collection,
        collectioncode,
        mandateinfo,
        firstcollection,
        signaturedate,
        defaultbank,
        Accountholder,
        accountnumber,
        IBAN,
        BICcode,
        NationalBankID,
        Bankname,
        bankaddress,
        bankaddressnumber,
        bankpostalcode,
        banklocation,
        bankstate,
        Reference,
        bankcountry,
        duedays,
        ebilling,
        ebillingemailadress,
        generalledgeraccount,
        creditlimit,
        creditmanager,
        blocked,
        authorised,
        segmentcode,
        remind,
        reminderemailaddress,
        comment,
        discountitem,
        Sendtype,
        Emailaddress,
    """
    dyn_settings = load_dynamic_settings()

    users = []
    headings = [
        'code',
        'name',
        'website',
        'defaultaddress',
        'addresstype',
        'Companyname',
        'Attentionof',
        'addressline1',
        'addressline2',
        'postcode',
        'City',
        'country',
        'telephone',
        'fax',
        'VATno',
        'CoRegno',
        'emailaddress',
        'collection',
        'collectioncode',
        'mandateinfo',
        'firstcollection',
        'signaturedate',
        'defaultbank',
        'Accountholder',
        'accountnumber',
        'IBAN',
        'BICcode',
        'NationalBankID',
        'Bankname',
        'bankaddress',
        'bankaddressnumber',
        'bankpostalcode',
        'banklocation',
        'bankstate',
        'Reference',
        'bankcountry',
        'duedays',
        'ebilling',
        'ebillingemailadress',
        'generalledgeraccount',
        'creditlimit',
        'creditmanager',
        'blocked',
        'authorised',
        'segmentcode',
        'remind',
        'reminderemailaddress',
        'comment',
        'discountitem',
        'Sendtype',
        'Emailaddress',
    ]
    if include_headings:
        users.append(headings)

    for cc3profile in queryset:
        profile = cc3profile.user.get_profile()

        iban = ''
        bic_code = ''
        try:
            profile_type, specific_profile = profile.get_profile_type(
                include_profile=True)
            if specific_profile:
                iban = specific_profile.iban
                bic_code = specific_profile.bic_code
        except:
            pass

        twinfield_user_code = dyn_settings.TWINFIELD_USER_CODE_TEMPLATE.format(
            profile.user.id)

        address_line = profile.address
        if hasattr(profile, 'num_street') and profile.num_street:
            address_line += ' {0}'.format(profile.num_street)
        if hasattr(profile, 'extra_address') and profile.extra_address:
            address_line += ' {0}'.format(profile.extra_address)

        user_email = profile.user.email

        ebilling_email = ', '.join(
            (user_email,) + BILLING_INVOICE_CC_EMAILS)

        comment = 'Community: {0}, Group: {1}'.format(
            profile.community.title, profile.cyclos_group.name)

        acc_holder = None

        if hasattr(profile, 'business_profile'):
            if profile.business_profile is not None:
                acc_holder = profile.business_profile.account_holder
        elif hasattr(profile, 'institution_profile'):
            if profile.institution_profile is not None:
                acc_holder = profile.institution_profile.account_holder
        elif hasattr(profile, 'charity_profile'):
            if profile.charity_profile is not None:
                acc_holder = profile.charity_profile.account_holder
        elif hasattr(profile, 'individual_profile'):
            if profile.individual_profile is not None:
                acc_holder = profile.individual_profile.account_holder

        users.append([
            twinfield_user_code,  # 'code',
            profile.business_name,  # 'name',
            '',  # 'website',
            'true',  # 'defaultaddress',
            'invoice',  # 'addresstype',
            profile.business_name,  # 'Companyname',
            '',  # 'Attentionof',
            '',  # 'addressline1',
            address_line,  # 'addressline2',
            profile.postal_code,  # 'postcode',
            profile.city,  # 'City',
            str(profile.country),  # 'country',
            profile.phone_number,  # 'telephone',
            '',  # 'fax',
            '',  # 'VATno',
            '',  # 'CoRegno',
            user_email,  # 'emailaddress',
            'false',  # 'collection',
            '',  # 'collectioncode',
            twinfield_user_code,  # 'mandateinfo',
            '',  # 'firstcollection',
            '',  # 'signaturedate',
            '',  # 'defaultbank',
            acc_holder,  # 'Accountholder',
            '',  # 'accountnumber',
            iban,  # 'IBAN',
            bic_code,  # 'BICcode',
            '',  # 'NationalBankID',
            '',  # 'Bankname',
            '',  # 'bankaddress',
            '',  # 'bankaddressnumber',
            '',  # 'bankpostalcode',
            '',  # 'banklocation',
            '',  # 'bankstate',
            '',  # 'Reference',
            '',  # 'bankcountry',
            DEFAULT_TERMS_DAYS,  # 'duedays',
            'true',  # 'ebilling',
            ebilling_email,  # 'ebillingemailadress',
            dyn_settings.TWINFIELD_GL_ACCOUNT_USERS,  # 'generalledgeraccount',
            '0.00',  # 'creditlimit',
            dyn_settings.TWINFIELD_CREDIT_MANAGER,  # 'creditmanager',
            'false',  # 'blocked',
            'true',  # 'authorised',
            '',  # 'segmentcode',
            'email',  # 'remind',
            ebilling_email,  # 'reminderemailaddress',
            comment,  # 'comment',
            '',  # 'discountitem',
            'ByEmail',  # 'Sendtype',
            user_email,  # 'Emailaddress',
        ])

    if not users:
        users = [[]]

    return users


def items_list_for_export(queryset, include_headings=True):
    """Generate the list of rows for the invoices csv

    queryset - Invoices to include

    Fields:
        Invoice type
        Debtor
        Number
        Invoice date
        Due date
        Header
        Footer
        Currency
        Quantity
        Article
        Sub article
        Description
        Unit price (VAT excluded)
        Unit price (VAT included)
        VAT code
        GL account
        Free textfield1
        Free textfield2
        Free textfield3
    """
    items = []
    headings = [
        'Invoice type',
        'Debtor',
        'Number',
        'Invoice date',
        'Due date',
        'Header',
        'Footer',
        'Currency',
        'Quantity',
        'Article',
        'Sub article',
        'Description',
        'Unit price (VAT excluded)',
        'Unit price (VAT included)',
        'VAT code',
        'GL account',
        'Free textfield1',
        'Free textfield2',
        'Free textfield3',
    ]
    dyn_settings = load_dynamic_settings()

    if include_headings:
        items.append(headings)

    #invoice_number = 0  # tells TF to generate separate invoices
    for invoice in queryset:
        #invoice_number += 1
        due_date = invoice.invoice_date + relativedelta(
            days=DEFAULT_TERMS_DAYS)
        user_code = dyn_settings.TWINFIELD_USER_CODE_TEMPLATE.format(
            invoice.user_profile.user.id)
        for item in invoice.items.all():
            product = item.assigned_product.product
            items.append([
                dyn_settings.TWINFIELD_INVOICE_TYPE,  # 'Invoice type',
                user_code,  # 'Debtor',
                #invoice_number,  # 'Number',  #  TODO: use Invoice.id??
                invoice.id,  # 'Number',
                invoice.invoice_date,  # 'Invoice date',
                due_date,  # 'Due date',
                invoice.description,  # 'Header',
                '',  # 'Footer',
                'EUR',  # 'Currency',
                item.quantity,  # 'Quantity',
                product.article_code,  # 'Article',
                product.subarticle_code,  # 'Sub article',
                '',  # 'Description',
                item.unit_price_ex_tax,  # 'Unit price (VAT excluded)',
                '',  # 'Unit price (VAT included)',
                '',  # 'VAT code', <- supplied in products file, not here
                '',  # 'GL account',
                dyn_settings.TWINFIELD_PROJECT_CODE,  # 'Free textfield1',
                '',  # 'Free textfield2',
                '',  # 'Free textfield3',
            ])
            if item.discount_amount_ex_tax:
                # add another item for the discount
                # there's no corresponding Product, so we have to supply
                # stuff like description here. Also assuming it's OK for
                # article code and subarticle code to be empty
                items.append([
                    dyn_settings.TWINFIELD_INVOICE_TYPE,  # 'Invoice type',
                    user_code,  # 'Debtor',
                    #invoice_number,  # 'Number',  #  TODO: use Invoice.id??
                    invoice.id,  # 'Number',
                    invoice.invoice_date,  # 'Invoice date',
                    due_date,  # 'Due date',
                    invoice.description,  # 'Header',
                    '',  # 'Footer',
                    'EUR',  # 'Currency',
                    1,  # 'Quantity',
                    '0',  # 'Article',  ('no match in products file')
                    '',  # 'Sub article',
                    item.discount_description,  # 'Description',
                    item.discount_amount_ex_tax,  # 'Unit price (VAT excl.)',
                    '',  # 'Unit price (VAT included)',
                    product.tax_regime.twinfield_code,  # 'VAT code',
                    dyn_settings.TWINFIELD_GL_ACCOUNT_PRODUCTS,  # 'GL account'
                    '',  # 'Free textfield1',
                    '',  # 'Free textfield2',
                    '',  # 'Free textfield3',
                ])

    if not items:
        items = [[]]

    return items


def get_invoices_csv(queryset, include_headings=True, encoding='utf-8'):
    """Return csv of all Invoices in queryset for Twinfield"""
    items = items_list_for_export(queryset, include_headings)
    return generate_csv(
        items, encoding=encoding, headers=[])


def get_products_csv(queryset, include_headings=True, encoding='utf-8'):
    """Return csv of all Products in queryset for Twinfield"""
    products = products_list_for_export(queryset, include_headings)
    return generate_csv(
        products, encoding=encoding, headers=[])


def get_users_csv(queryset, include_headings=True, encoding='utf-8'):
    """Return csv of all CC3Profiles in queryset for Twinfield"""
    users = users_list_for_export(queryset, include_headings)
    return generate_csv(
        users, encoding=encoding, headers=[])


def get_invoices_xls(queryset, include_headings=True, encoding='utf-8'):
    """Return xls of all Invoices in queryset for Twinfield"""
    items = items_list_for_export(queryset, include_headings)
    return generate_xls(items, encoding=encoding, headers=[])


def get_products_xls(queryset, include_headings=True, encoding='utf-8'):
    """Return xls of all Products in queryset for Twinfield"""
    products = products_list_for_export(queryset, include_headings)
    return generate_xls(products, encoding=encoding, headers=[])


def get_users_xls(queryset, include_headings=True, encoding='utf-8'):
    """Return xls of all CC3Profiles in queryset for Twinfield"""
    users = users_list_for_export(queryset, include_headings)
    return generate_xls(users, encoding=encoding, headers=[])


def get_custom_csv_from_sql(sql_name, invoice_date, period_start, period_end):
    """Run the SQL and return the resulting csv file

    NB. Grubby, and currently NOT USED
    TODO: Delete once we're sure it's not needed
    """
    import subprocess
    import tempfile
    from .sql import MONTHLY_EXTRA_TWINFIELD_SQL, SQL_DATE_FORMAT

    temp_filename = os.path.join("/", "tmp",
                                 "{0}_{1}.csv".format(sql_name, datetime.now().isoformat()))

    _sql = MONTHLY_EXTRA_TWINFIELD_SQL[sql_name]
    _sql = _sql.replace(
        '{{CYCLOS_DB_NAME}}', 'cyclos3').replace(
        '{{DJANGO_DB_NAME}}', 'icare4u_front').replace(
        '{{OUTPUT_FILE}}', temp_filename).replace(
        '{{INVOICE_DATE}}', invoice_date.strftime(SQL_DATE_FORMAT)).replace(
        '{{PERIOD_END_DATE}}', invoice_date.strftime(SQL_DATE_FORMAT)).replace(
        '{{PERIOD_START_DATE}}', invoice_date.strftime(SQL_DATE_FORMAT))

    LOG.debug(_sql)

    p = subprocess.Popen(['mysql', '-ureporter', '-preporter'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    output, err = p.communicate(_sql)

    if err:
        LOG.error("Error executing SQL: {0}".format(err))

    with open(temp_filename, 'r') as f:
        csv = f.read()

    return csv, err

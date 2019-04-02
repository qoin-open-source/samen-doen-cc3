import os
from setuptools import setup, find_packages


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


install_requires = [
    # main modules
    'Django>=1.8, <1.9a0',
    'mysqlclient==1.3.10',
    # 'Sphinx',
    # 'South>=1.0,<1.1',
    'Pillow>=3.2.0, <3.13a0',

    #############################
    #   Django 3rd party apps   #
    #############################
    #    'cmsplugin_vimeo==0.1', # moved to child project
    'dj_database_url>=0.2.2',
    'django-admin-sortable==2.0.16',
    'django-ajax-selects==1.4.3',
    'django-autoslug==1.9.3',
    'django-axes==1.7',
    'django-cms>=3.3,<=3.4a1',
    'html5lib==0.9999999', # PIN as djangocms-text-ckeditor is fussy
    'djangocms-admin-style==1.2.2',
    'djangocms-file==1.0.0',
    'djangocms-flash==0.3.0',
    'djangocms-googlemap==0.4.0',
    'djangocms-inherit==0.2.1',
    'djangocms-link>=1.7.2,<1.9a0',
    'djangocms-picture==1.0.0',
    'djangocms-snippet==1.8.1',
    'djangocms-teaser==0.2.0',
    'djangocms-text-ckeditor==3.0.0',
    'djangocms_twitter==0.0.5',
    'djangocms_video==1.0.0',
    'django-ckeditor-updated==4.4.4',
    'django_compressor==1.4',
    'django-countries==3.4.1',
    'django-endless-pagination==2.0',
    'django-extra-views==0.7.1',
    'django-formtools==1.0.0',
    #    'django-filer==0.9.5',     # getting to grips with djangoCMS 3 first.
                                # django-filer has alternative plugins
    'django-filter>=0.13.0,<=0.14a0',
    'django-form-designer-ai==0.10.0',
    'django-nvd3==0.9.7',
    'django-overextends==0.4.1',
    'django-pagination==1.0.7',
    'django-picklefield==0.3.2',
    'djangorestframework==3.2.5',
    'django-registration-redux==1.4',
    'django-reversion>=0.10.0,<2.0a0',
#    'django-rosetta==0.7.11',
    'django-taggit==0.19.1',
    'django-tinymce==2.3.0',
    'django-formtools==1.0.0',
    'Jinja2>=2.7.2',  # django-nvd3 has a requirement for python-nvd3,
    'python-slugify==1.1.4',  # which should load Jinja and python-slugify
    'astroid==1.4.6',
#    'djoser==0.3.1',
    'easy-thumbnails==2.3',
    'PySimpleSOAP==1.05a',  # 1.10 upsets things by removing 'trace'
    # from SoapClient __init__ args
    # > 1.10 aren't pip installable - not in PyPI?
    'httplib2',
    'iso8601==0.1.11',
    'pycurl==7.43.0',
    'raven==5.2.0',
    'reportlab==3.3',
    'xlwt==1.1.2',
    'wsgiref==0.1.2',
    'Unipath==1.1',
    'django-oauth-toolkit>=0.7.2,<1.0a1',  # For oauth2 provider usage in the API
    'factory-boy>=2.4.1',  # For tests that use factories
    'python-dateutil==2.5.3',
    'rdoclient==1.0.2',  # for prizedraw app
    'djoser==0.4.3',    # for djangorestframework < 3.0
    'geopy==1.11.0',
]

setup(
    name='cc3',
    version='sd_v2.5.1',
    author=u'Stephen Wolff',
    author_email='stephen.wolff@qoin.org',
    description='Set of Django apps for use with Cyclos',
    license='None yet. Purely for Qoin projects',
    url='https://github.com/qoin-open-source/samen-doen-cc3.git',
    packages=find_packages(exclude=('docs', 'tests')),
    long_description=read('README'),
    zip_safe=False,
    install_requires=install_requires,
    dependency_links=dependency_links
)

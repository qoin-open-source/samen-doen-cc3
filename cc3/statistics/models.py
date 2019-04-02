import datetime
import importlib
import logging
import random
import time

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .sql import COMMON_SQL
from .utils import run_custom_sql, run_cyclos_sql


# import custom SQL if configured
custom_sql_module = getattr(settings,
        'STATS_CUSTOM_SQL_MODULE', None)
if custom_sql_module:
    CUSTOM_SQL = importlib.import_module(
            custom_sql_module).CUSTOM_SQL
else:
    CUSTOM_SQL = {}


LOG = logging.getLogger(__name__)


GRAPH_TYPE_TABLE = 'T'
GRAPH_TYPE_BAR_GRAPH = 'B'
GRAPH_TYPE_MULTI_BAR_GRAPH = 'M'
GRAPH_TYPE_CHOICES = (
    (GRAPH_TYPE_TABLE, _('Table')),
    (GRAPH_TYPE_BAR_GRAPH, _('Bar Graph')),
    (GRAPH_TYPE_MULTI_BAR_GRAPH, _('Multi Bar Graph')),
)

X_TYPE_YEARMONTH = 'DATE_YM'
X_TYPE_CHOICES = (
    (X_TYPE_YEARMONTH, _("Year and month ('YYYYMM')")),
)


class Dashboard(models.Model):
    title = models.CharField(max_length=64,
                             help_text=_(u"Focus of statistics area"))
    sequence = models.IntegerField(
        help_text=_(u"Order of dashboards"))
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _(u"Dashboard")
        verbose_name_plural = _(u"Dashboard")
        ordering = ['sequence']

    def annotated_graphs(self):
        """Return self.graph_set annotated with the community_filter_code
        """
        # ugh! -- on reflection, maybe could have used a template tag with
        # model and community_filter_code as params
        community_filter_code = getattr(self, 'community_filter_code', '')
        return self.graph_set.extra(select = {
            'community_filter_code': "'{0}'".format(community_filter_code)})



class Graph(models.Model):
    title = models.CharField(max_length=255,
                             help_text=_(u"Title of the graph"))
    dashboard = models.ForeignKey('Dashboard')
    active = models.BooleanField(default=True)
    sequence = models.IntegerField(
        help_text=_(u"Placement in dashboard of graphs"))
    raw_sql = models.TextField(blank=True, default='',
        help_text=_(u"SQL to run to collect data for graph"))
    sql_key = models.CharField(
        max_length=50, blank=True, default='',
        help_text=_(u"Key identifying SQL to run to collect data for graph "
                    "(only used if no Raw SQL supplied)"))
    use_cyclos_database = models.BooleanField(default=False, help_text=_(
        u"When set to true, raw_sql is run against the cyclos database"
    ))
    graph_type = models.CharField(
        max_length=1, choices=GRAPH_TYPE_CHOICES, blank=True, default='',
        help_text=_(u"Graph type or leave blank"))
    width = models.IntegerField(default=300,
                                help_text=_(u"Width of graph on page"))
    height = models.IntegerField(default=400,
                                 help_text=_(u"Height of graph on page"))
    x_type = models.CharField(
        max_length=12, choices=X_TYPE_CHOICES, blank=True, default='',
        help_text=_(u"Special treatment for x values, or leave blank"))
    x_output_format = models.CharField(
        max_length=50, blank=True, default='',
        help_text=_(u"Output format for x values (depending on x type), or leave blank"))
    x_max_columns = models.IntegerField(blank=True, null=True,
        help_text=_(u"Limit the number of x columns shown"))
    table_add_totals_row = models.BooleanField(default=False, help_text=_(
        u"Add a 'Totals' row to table"
    ))

    class Meta:
        ordering = ['sequence']

    @property
    def chartcontainer(self):
        q = ""
        for i in self.dashboard.title:
            if i.isalpha():
                q = "".join([q, i])
        return u"%sgraph%s" % (
            q.lower(),
            self.pk
        )

    @property
    def charttype(self):
        if self.graph_type == GRAPH_TYPE_TABLE:
            return u"tabulatedData"
        if self.graph_type == GRAPH_TYPE_BAR_GRAPH:
            return u"discreteBarChart"
        if self.graph_type == GRAPH_TYPE_MULTI_BAR_GRAPH:
            return u"multiBarChart"

        return u""

    @property
    def chartdata(self):
        chartdata_to_return = {}
        data = []
        community_filter_code = getattr(self, 'community_filter_code', '')
        raw_sql = self._get_raw_sql(community_filter_code=community_filter_code)
        #LOG.debug("raw_sql: {0}".format(raw_sql))
        if raw_sql:
            try:
                # TODO protect Raw SQL usage against destructive queries
                # ie filter out/raise exception for
                #  SELECT INTO, UPDATE, DELETE etc
                # here or at a model save level?
                if self.use_cyclos_database:
                    data = run_cyclos_sql(raw_sql, [])
                else:
                    data = run_custom_sql(raw_sql, [])
                #LOG.debug(data)
            except Exception, e:
                # TODO work out what kind of SQL exceptions can be thrown here
                print e

        if self.graph_type == GRAPH_TYPE_TABLE:
            # example SQL;
            # - see statistics/sql/icare4u_userstats_1.sql

            # need to convert
            # [
            #   {'User type': u'Spaarders', 'Total number': Decimal('151'),
            # 'Transacting/active users': Decimal('144')},
            #   {'User type': u'Businesses', 'Total number': Decimal('15'),
            # 'Transacting/active users': Decimal('15')},
            #   {'User type': u'Spaardoelen', 'Total number': Decimal('11'),
            # 'Transacting/active users': Decimal('11')},
            #   {'User type': u'Instelligen', 'Total number': Decimal('7'),
            # 'Transacting/active users': Decimal('7')}
            # ]
            # into:
            # { 'x': ['User type', 'Total number', 'Transacting/active users'],
            #   'data': [
            #       {'y': [151, 144], 'name': 'Spaarders'},
            #       {'y': [15, 15], 'name': 'Businesses'},
            #       {'y': [11, 11], 'name': 'Sppardoenlen'}
            #       {'y': [7, 7], 'name': 'Instelligen'}
            #   ]
            # }
            xdata = data[0].keys()
            ydata = []
            for _dict in data:
                ydata_dict = {}
                _count = 0
                for k, v in _dict.items():
                    if _count == 0:
                        ydata_dict['name'] = v
                    else:
                        if 'y' in ydata_dict:
                            ydata_dict['y'].append(v)
                        else:
                            ydata_dict['y'] = [v, ]
                    _count += 1
                ydata.append(ydata_dict)

            if self.table_add_totals_row:

                cols = [row['y'] for row in ydata]
                totals = [sum(x) for x in zip(*cols)]
            else:
                totals = []

            # x_max_columns currently ignored for table

            chartdata_to_return = {
                'x': xdata,
                'data': ydata,
                'totals': totals,
            }

        if self.graph_type == GRAPH_TYPE_BAR_GRAPH:
            # example SQL;
            # - see statistics/sql/icare4u_userstats_2.sql
            xdata = []
            ydata = []
            for _dict in data:
                for k, v in _dict.items():
                    if k == 'x':
                        xdata.append(str(v))
                    if k == 'y1':
                        # (just v didn't work when v was Decimal)
                        ydata.append(float(v))

            # trim data if max columns specified
            if self.x_max_columns is not None and self.x_max_columns < len(xdata):
                slice_start = len(xdata) - self.x_max_columns
                xdata = xdata[slice_start:]
                ydata = ydata[slice_start:]

            chartdata_to_return = {
                'x': self._process_xdata(xdata),
                'y': ydata,
            }

        if self.graph_type == GRAPH_TYPE_MULTI_BAR_GRAPH:
            # example SQL;
            # - see statistics/sql/icare4u_userstats_3.sql
            xdata = []

            # data =
            # [
            #   {'x': 201410, 'y1': 5L, 'y2': None, 'y3': None, 'name': 'Businesses'},
            #   {'x': 201411, 'y1': 1L, 'y2': None, 'y3': None, 'name': 'Businesses'},
            #   {'x': 201501, 'y1': 7L, 'y2': None, 'y3': None, 'name': 'Businesses'},
            #   {'x': 201502, 'y1': 1L, 'y2': None, 'y3': None, 'name': 'Businesses'},
            #   {'x': 201501, 'y1': 1L, 'y2': None, 'y3': None, 'name': 'Businesses'},
            #   {'x': 201501, 'y1': None, 'y2': 4L, 'y3': None, 'name': 'Institutions'},
            #   {'x': 201502, 'y1': None, 'y2': 2L, 'y3': None, 'name': 'Institutions'},
            #   {'x': 201508, 'y1': None, 'y2': 1L, 'y3': None, 'name': 'Institutions'},
            #   {'x': 201410), 'y1': None, 'y2': None, 'y3': 8L, 'name': 'Spaardoelen'},
            #   {'x': 201501, 'y1': None, 'y2': None, 'y3': 1L, 'name': 'Spaardoelen'},
            #   {'x': 201502, 'y1': None, 'y2': None, 'y3': 2L, 'name': 'Spaardoelen'}
            # ]

            # get all X values
            for _dict in data:
                for k, v in _dict.items():
                    if k == 'x':
                        if str(v) not in xdata:
                            xdata.append(str(v))

            # sort the dates
            sorted(xdata)

            # get all yN values and series names
            ydata_dict = {}
            name_dict = {}
            for _dict in data:
                for k, v in _dict.items():
                    if k not in ['x', 'name']:
                        if str(k) not in ydata_dict:
                            ydata_dict[str(k)] = [0] * len(xdata)
                        if v:
                            str_date = str(_dict['x'])
                            if str_date in xdata:
                                index_of_date_in_xdata = xdata.index(str_date)
                                ydata_dict[str(k)][index_of_date_in_xdata] = v
                            yname = _dict.get('name', '')
                            if yname:
                                name_dict[k.replace('y', 'name')] = yname

            # {
            # 'name4': 'series 4',
            # 'name2': 'series 2',
            # 'name3': 'series 3',
            # 'name1': 'series 1',
            # 'y1': [4, 9, 3, 5, 10, 3, 9, 1, 6, 6],
            # 'y3': [12, 27, 9, 15, 30, 9, 27, 3, 18, 18],
            # 'y2': [8, 18, 6, 10, 20, 6, 18, 2, 12, 12],
            # 'y4': [16, 36, 12, 20, 40, 12, 36, 4, 24, 24],
            # 'extra1': {'tooltip': {'y_end': ' calls', 'y_start': 'There are '}},
            # 'extra2': {'tooltip': {'y_end': ' calls', 'y_start': 'There are '}},
            # 'extra3': {'tooltip': {'y_end': ' calls', 'y_start': 'There are '}},
            # 'extra4': {'tooltip': {'y_end': ' calls', 'y_start': 'There are '}},
            # 'x': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            # }

            # trim data if max columns specified
            if self.x_max_columns is not None and self.x_max_columns < len(xdata):
                slice_start = len(xdata) - self.x_max_columns
                xdata = xdata[slice_start:]
                for yname, ylist in ydata_dict.items():
                    ydata_dict[yname] = ylist[slice_start:]

            chartdata_to_return = {
                'x': self._process_xdata(xdata),
            }
            chartdata_to_return.update(ydata_dict)
            chartdata_to_return.update(name_dict)

        #LOG.debug("chartdata: {0}".format(chartdata_to_return))
        return chartdata_to_return

    @property
    def extra(self):
        # (from nvd3_tags) extra settings:
        # ``x_is_date`` - if enabled the x-axis will be display as date format
        # ``x_axis_format`` - set the x-axis date format, ie. "%d %b %Y"
        # ``tag_script_js`` - if enabled it will add the javascript tag '<script>'
        # ``jquery_on_ready`` - if enabled it will load the javascript only when page is loaded
        #    this will use jquery library, so make sure to add jquery to the template.
        # ``color_category`` - Define color category (eg. category10, category20, category20c)
        # ``chart_attr`` - Custom chart attributes
        #
        # NB. we're dealing with x_is_date and x_axis_format ourselves
        # for i18n/l10n reasons
        extra = {
            'tag_script_js': True,
            'jquery_on_ready': False,
            'color_category': 'category10',
        }
        if self.graph_type == GRAPH_TYPE_MULTI_BAR_GRAPH:
            extra['x_axis_format'] = ""
        return extra


    def _get_raw_sql(self, community_filter_code):
        """Returns the sql to be executed

        Starts with db field, and if that's empty looks for coded snippet,
        first project-specific, then common
        """
        raw_sql = ''
        if self.raw_sql:
            raw_sql = self.raw_sql
        if self.sql_key:
            try:
                raw_sql = CUSTOM_SQL[self.sql_key]
            except KeyError:
                raw_sql = COMMON_SQL[self.sql_key]

        if '{{community_filter}}' in raw_sql:
            # replace it with the filter code
            if community_filter_code:
                if self.use_cyclos_database:
                    filter_str = "cfv.string_value='{0}' AND "
                else:
                    filter_str = "community.code='{0}' AND "
                filter_sql = filter_str.format(community_filter_code)
            else:
                filter_sql = ""
            raw_sql = raw_sql.replace('{{community_filter}}', filter_sql)

        return raw_sql


    def _process_xdata(self, xdata):
        """Re-format xdata according to x_type"""
        # TODO: might also want to fill in missing months?

        if self.x_type == X_TYPE_YEARMONTH:
            if self.x_output_format:
                fmt = self.x_output_format
            else:
                fmt = '%b %Y'
            return [
                datetime.datetime.strptime(val, '%Y%m'
                                           ).strftime(fmt) for val in xdata]
        return xdata

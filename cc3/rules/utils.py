import datetime
from datetime import timedelta
import importlib
import logging

from django.utils import timezone

LOG = logging.getLogger(__name__)


def str_to_class(module_name, class_name):
    try:
        module_ = importlib.import_module(module_name)
        try:
            class_ = getattr(module_, class_name)()
        except AttributeError:
            LOG.error('Class {0} does not exist'.format(class_name))
    except ImportError:
        LOG.error('Module {0} does not exist'.format(module_name))
    return class_ or None


def last_month_first_of_month():

    today = timezone.now()
    this_month_first_of_month = datetime.date(today.year, today.month, 1)
    new_date = this_month_first_of_month - timedelta(days=1)
    last_month_first = datetime.date(new_date.year, new_date.month, 1)
    LOG.debug(last_month_first)
    return last_month_first
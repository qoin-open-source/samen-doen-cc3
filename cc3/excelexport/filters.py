from django.forms.utils import to_current_timezone


# Admin XLS export field filter to remove timezone awareness
# from datetime.datetime objects
class MakeTimezoneNaiveFilter(object):
    @staticmethod
    def apply(datetime_obj):
        if datetime_obj:
            return to_current_timezone(datetime_obj)
        else:
            return None

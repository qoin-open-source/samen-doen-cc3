from ajax_select import LookupChannel  #, #register,
from .models import CardNumber


#@register('number')
class CardNumbersLookup(LookupChannel):

    model = CardNumber

    def get_query(self, q, request):
        return self.model.objects.filter(number__contains=q).order_by('number')

    def get_result(self, obj):
        return obj.number

#    def format_item_display(self, item):
#        return u"%s" % item

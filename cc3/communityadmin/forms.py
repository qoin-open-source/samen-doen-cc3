from django import forms
from django.conf import settings
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _

from tinymce.widgets import TinyMCE

from cc3.core.widgets import CheckboxSelectMultipleCategoriesTree
from cc3.core.models import Category
from cc3.marketplace.common import AD_STATUS_CHOICES
from cc3.marketplace.models import Ad, AdType
from cc3.marketplace.widgets import (
    PiraatSidebarCheckboxSelectMultiple, OfferWantCheckboxSelectMultiple,
    PiraatCheckboxSelectMultipleCategoriesTree)
from cc3.cyclos.models import CommunityMessage, CyclosGroup


class OffersWantsForm(forms.Form):
    """
    Form for filtering marketplace.
    """
    adtype = forms.ModelMultipleChoiceField(
        queryset=AdType.objects.filter(active=True),
        widget=OfferWantCheckboxSelectMultiple, required=False)
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(active=True),
        widget=PiraatSidebarCheckboxSelectMultiple, required=False)
    status = forms.MultipleChoiceField(choices=AD_STATUS_CHOICES,
        widget=PiraatSidebarCheckboxSelectMultiple, required=False)


class AdHoldForm(forms.ModelForm):
    class Meta:
        model = Ad
        fields = ('status',)


class CommunityAdminAdForm(forms.ModelForm):
    DESC_LIMIT = 300

    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(active=True),
        widget=PiraatCheckboxSelectMultipleCategoriesTree,
        label=_(u"Categories"),
        error_messages={'required': _(u'Please select a category')})

    description = forms.CharField(
        widget=TinyMCE(
            mce_attrs=dict(
                settings.TINYMCE_SIMPLE_CONFIG.items() +
                [('charLimit', DESC_LIMIT)]
            )),
        label=_(u"Description")
    )

    price = forms.DecimalField(
        label=_(u"Price"), max_digits=10, min_value=0.00, decimal_places=2,
        error_messages={'required': _(u'Please enter a price')},
        required=False, localize=True)

    def __init__(self, *args, **kwargs):
        super(CommunityAdminAdForm, self).__init__(*args, **kwargs)
        self.community_id = None

    def set_community_id(self, _community_id):
        self.community_id = _community_id

    def clean(self):
        cd = self.cleaned_data
        if (cd.get('price', None) is None and cd.get('price_option', None) is None) or \
                (cd.get('price', None) is not None and cd.get('price_option', None) is not None):
            raise forms.ValidationError(
                _(u"Either a price or a price option is required."))
        return cd

    def clean_created_by(self):
        data = self.cleaned_data.get('created_by', None)

        if data:
            if data.community.id != self.community_id:
                raise forms.ValidationError(
                    _("The member is not part of your community"))
            if data.groupset and not data.groupset.may_add_ads:
                raise forms.ValidationError(
                    _('The member may not have ads, based on their groupset '
                      '({0})'.format(unicode(data.groupset))))
        return data

    class Meta:
        model = Ad
        fields = ('created_by', 'title', 'adtype', 'description',
                  'price', 'price_option', 'category', 'keywords',
                  'status')

    class Media:
        js = ('js/edit_ad.js',)


class CommunityAdminAdUpdateForm(forms.ModelForm):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(active=True),
        widget=CheckboxSelectMultipleCategoriesTree,
        label=_(u"Categories"),
        error_messages={'required': _(u'Please select a category')}
    )

    description = forms.CharField(
        widget=TinyMCE(mce_attrs=settings.TINYMCE_SIMPLE_CONFIG),
        label=_(u"Description")
    )

    price = forms.DecimalField(
        label=_(u"Price"), max_digits=10, min_value=0.00, decimal_places=2,
        required=False, localize=True)

    def __init__(self, *args, **kwargs):
        super(CommunityAdminAdUpdateForm, self).__init__(*args, **kwargs)
        self.community_id = None

    def clean(self):
        cd = self.cleaned_data
        if settings.PRICING_SUPPORT and (cd.get('price', None) is None and cd.get('price_option', None) is None) or \
                (cd.get('price', None) is not None and cd.get('price_option', None) is not None):
            raise forms.ValidationError(
                _(u"Either a price or a price option is required."))
        return cd

    class Meta:
        model = Ad
        fields = ('title', 'adtype', 'description',
                  'price', 'price_option', 'category', 'keywords',
                  'status')

    class Media:
        js = ('js/edit_ad.js',)


class CommunityMessageForm(forms.ModelForm):
    def save(self, commit=True):
        super(CommunityMessageForm, self).save(commit)
        self.instance.plugin.page.publish()

    class Meta:
        model = CommunityMessage
        fields = ('body',)
        widgets = {
            'body': TinyMCE(),
        }


class ChangeGroupForm(forms.Form):
    """ Groups for community. """
    groups = forms.ModelChoiceField(
        queryset=CyclosGroup.objects,
        widget=forms.RadioSelect, required=True, empty_label=None)
    comments = forms.CharField(
        widget=Textarea, label=_(u"Reason for group change"), required=True,
        max_length=180)

    def __init__(self, *args, **kwargs):
        super(ChangeGroupForm, self).__init__(*args, **kwargs)
        self.original_group_id = None

    def set_original_group_id(self, _original_group_id):
        self.original_group_id = _original_group_id

    def clean_groups(self):
        data = self.cleaned_data.get('groups')
        if data.id == self.original_group_id:
            raise forms.ValidationError(_('You have not changed the group'))

        return data


class CommunityAdminCreatedByForm(forms.Form):
    """
    Form for retrieving business email address from contact name.
    """
    created_by_name = forms.CharField()


class CommunityAdminCategoriesForm(forms.Form):
    """
    Form for retrieving categories for a profile
    """
    profile_id = forms.IntegerField()
    ad_code = forms.CharField(required=False)

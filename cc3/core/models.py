from adminsortable.fields import SortableForeignKey
from adminsortable.models import Sortable
from django.conf import settings
from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _
from django_countries.fields import CountryField


class CategoryManager(models.Manager):
    def for_businesses(self):
        """
        Return all Categories that have visible Businesses
        """
        return self.active().exclude(cc3profile__isnull=True).filter(
            cc3profile__is_visible=True).filter(
                cc3profile__groupset__is_visible=True).distinct()

    def for_ads(self):
        """
        Return all Categories that have visible Ads
        """
        return self.active().exclude(ad__isnull=True).distinct()

    def active(self):
        return self.model.objects.filter(active=True)


class Category(Sortable):
    parent = SortableForeignKey(
        'self', null=True, blank=True, related_name='children')
    title = models.CharField(max_length=100, help_text=(_(u'Category title')))
    description = models.CharField(
        max_length=255, help_text=(_(u'Category description')))
    active = models.BooleanField(
        default=True, help_text=_(u'Marks this Category as active'))
    ignore_for_matching = models.BooleanField(
        default=False,
        help_text=_(u"Don't report matching wants/offers for this Category"))

    objects = CategoryManager()

    class Meta(Sortable.Meta):
        verbose_name_plural = _(u'categories')
        ordering = ('order', 'title')

    def __unicode__(self):
        return u'{0}'.format(self.get_title())

    def _get_translation(self):
        current_language = get_language()
        try:
            translation = self.categorytranslation_set.get(
                language=current_language)
            return translation
        except CategoryTranslation.DoesNotExist:
            pass  # will try something else

        # try for languages like en-us
        if current_language.find('-') >= 0:
            language = current_language.split('-')[0]
            try:
                translation = self.categorytranslation_set.get(
                    language=language)
                return translation
            except CategoryTranslation.DoesNotExist:
                return None

        return None

    def get_title(self):
        translation = self._get_translation()
        return translation.title if translation else self.title

    def get_description(self):
        translation = self._get_translation()
        return translation.description if translation else self.description


class CategoryTranslation(models.Model):
    title = models.CharField(max_length=50, help_text=(_(u'Category title')))
    description = models.CharField(max_length=255)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)
    category = models.ForeignKey('core.Category', null=True, blank=True)

    class Meta:
        unique_together = ("language", "category")

    def __unicode__(self):
        return u"{0}".format(self.title)


class TrackedProfileCategory(models.Model):
    """
    Records when new want/offer categories added to a profile

    Only used if settings.TRACK_PROFILE_CATEGORIES is set
    """
    # This could have been used as the 'through' table for
    # CC3Profile.categories and .want_categories, but done this way
    # to minimise disruption. to existing code
    profile = models.ForeignKey('cyclos.CC3Profile')
    category = models.ForeignKey(Category)
    TYPE_OFFER = 'offer'
    TYPE_WANT = 'want'
    category_type = models.CharField(
        max_length=5,
        choices=((TYPE_OFFER, 'Offer'), (TYPE_WANT, 'Want')))
    time_added = models.DateTimeField(auto_now_add=True)


class Transaction(models.Model):
    """
    General transactions model. Specific transactions in CC3 project apps
    should subclass this one. In that way, we have a general registry of all
    the transactions (in this ``core`` app) and registries of specific types
    of transactions in their own apps.
    """
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    sender = models.ForeignKey(
        'cyclos.User', related_name='payment_sender')
    receiver = models.ForeignKey(
        'cyclos.User', related_name='payment_receiver')
    date_created = models.DateTimeField(_(u'Date created'), auto_now_add=True)
    transfer_id = models.IntegerField(
        default=0,
        help_text=_(u'Cyclos transaction ID - can be used for chargeback'))
    report_date = models.DateTimeField(
        _(u'Report date'), null=True, blank=True)


class LocationMixin(models.Model):
    """
    Model mixin for anything that needs an address

    Aims to have all the location-related fields (including project-
    custom ones such as 'num_street' and 'extra_address' (aka 'toevoeging')
    from Samen Doen and Troeven)
    """
    country = CountryField(_('Country'), blank=True, default='')
    city = models.CharField(_('City'), max_length=255, blank=True, default='')
    num_street = models.CharField(max_length=50, default='', blank=True)
    address = models.CharField(
        _('Address'), max_length=255, blank=True, default='')
    extra_address = models.CharField(max_length=255, default='', blank=True)
    postal_code = models.CharField(
        _('Postal code'), max_length=10, blank=True, default='')
    latitude = models.DecimalField(
        null=True,
        blank=True,
        max_digits=17,
        decimal_places=14)
    longitude = models.DecimalField(
        null=True,
        blank=True,
        max_digits=17,
        decimal_places=14)
    map_zoom = models.IntegerField(
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    """
    Model mixin to enforce only one record. Use for e.g. settings
    (Based on
    http://steelkiwi.com/blog/practical-application-singleton-design-pattern/
    but ditched the cacheing because it didn't work and probably doesn't
    add much)
    """
    class Meta:
            abstract = True

    def delete(self, *args, **kwargs):
            pass

    def save(self, *args, **kwargs):
            self.pk = 1
            super(SingletonModel, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

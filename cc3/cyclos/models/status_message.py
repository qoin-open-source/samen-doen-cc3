from django.conf import settings
from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _


class StatusMessage(models.Model):
    """
    Message shown to user at different points during the process post
    registration.
    These are to encourage participation, and are tracked for at least one
    status to check that the user is not presented the message too many times.

    Translations are handled as per AdCategories.
    """
    user_status = models.ForeignKey('UserStatus')
    title = models.CharField(max_length=50, help_text=(_(u'Default title')))
    message = models.CharField(
        max_length=255, help_text=(_(u'Default message, shown to user')))
    link = models.CharField(
        max_length=255, blank=True, default='',
        help_text=(_(u'Reverse ID of page to link to (ask a system '
                     u'administrator!)')))
    link_text = models.CharField(
        max_length=255, blank=True, default='',
        help_text=(_(u'Text for link')))
    status_message_level = models.ForeignKey('StatusMessageLevel')
    appearance_limit = models.IntegerField(
        null=True, blank=True,
        help_text=(_('Number of times a message should appear to a user '
                     '(optional).')))

    class Meta:
        app_label = 'cyclos'
        verbose_name_plural = _(u'status messages')
        unique_together = ('user_status', 'title')
        ordering = ['pk']

    def __unicode__(self):
        return u'{0}'.format(self.get_title())

    def _get_translation(self):
        current_language = get_language()
        try:
            translation = self.statusmessagetranslation_set.get(
                language=current_language)
            return translation
        except StatusMessageTranslation.DoesNotExist:
            pass # will try something else

        # try for languages like en-us
        if current_language.find('-') >= 0:
            language = current_language.split('-')[0]
            try:
                translation = self.statusmessagetranslation_set.get(
                    language=language)
                return translation
            except StatusMessageTranslation.DoesNotExist:
                return None

        return None

    def get_title(self):
        translation = self._get_translation()
        return translation.title if translation else self.title

    def get_message(self):
        translation = self._get_translation()
        return translation.message if translation else self.message

    def get_link_text(self):
        translation = self._get_translation()
        return translation.link_text if translation else self.link_text


class StatusMessageAppearance(models.Model):
    """
    Count how many times a message appears to a user, so that a limit
    can be set for messages.
    """
    message = models.ForeignKey('StatusMessage')
    user = models.ForeignKey('cyclos.User')
    count = models.IntegerField(default=0)

    class Meta:
        app_label = 'cyclos'
        unique_together = ('message', 'user')


class StatusMessageTranslation(models.Model):
    title = models.CharField(
        max_length=50, help_text=(_(u'Status Message title')))
    message = models.CharField(
        max_length=255, help_text=(_(u'Status message')))
    link_text = models.CharField(
        max_length=255, blank=True, default='',
        help_text=(_(u'Text for link')))
    language = models.CharField(max_length=5, choices=settings.LANGUAGES)
    status_message = models.ForeignKey('StatusMessage', null=True, blank=True)

    class Meta:
        app_label = 'cyclos'
        unique_together = ('language', 'status_message')

    def __unicode__(self):
        return u'{0}'.format(self.title)


class UserStatus(models.Model):
    """
    1. New users who haven't created their profile - "You need to complete your
    profile" with link to the profile page. 

    2. Users who have completed their profile but not placed any ads: Place 
    first ad "Now you've completed your profile, you should post an offer or a
    request for something" 

    3. Users who have placed at least one ad but have not bought anything
    (ie: do not have any transactions): "Browse the marketplace to see if
    other members are offering what you need"

    4. Users who have made at least one transaction but do not have a credit
    line (are not subscribed members): "Request a credit line and you can do
    more in Tradeqoin"

    5. Users who have created at least one ad and made at least one purchase:
    "Consider starting your own community" and link to a CMS page.
    (This message should maybe be set to expire after being shown to the user
     a set number of times)
    """
    code = models.CharField(
        max_length=10, help_text="User status code, used in code to identify")
    description = models.CharField(max_length=255)

    class Meta:
        app_label = 'cyclos'
        verbose_name_plural = _(u'user statuses')
        unique_together = ('code', 'description')
        ordering = ['pk']

    def __unicode__(self):
        return u'{0}'.format(self.description)


class StatusMessageLevel(models.Model):
    """
    show info or warn CSS? (others may follow)
    """
    css_class = models.CharField(max_length=15)
    description = models.CharField(max_length=255)

    class Meta:
        app_label = 'cyclos'

    def __unicode__(self):
        return u'{0}'.format(self.description)

from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

from cc3.cyclos.models import (
    CC3Profile, StatusMessage, StatusMessageAppearance)
from cc3.marketplace.models import Ad, AdPaymentTransaction

register = template.Library()


@register.inclusion_tag('cyclos/user_status.html', takes_context=True)
def user_status(context):
    """
    Returns user status message as necessary.

    1. NEW: New users who haven't created their profile - "You need to
    complete your profile" with link to the profile page.

    2. NOADS: Users who have completed their profile but not placed any ads:
    Place first ad "Now you've completed your profile, you should post an offer
    or a request for something".

    3. NOBUY: Users who have placed at least one ad but have not bought
    anything (ie: do not have any transactions): "Browse the marketplace to see
    if other members are offering what you need".

    4. NOCREDIT: Users who have made at least one transaction but do not have a
    credit line (are not subscribed members): "Request a credit line and you
    can do more in Tradeqoin".

    5. AD_N_BUY: Users who have created at least one ad and made at least one
    purchase: "Consider starting your own community" and link to a CMS page.
    (This message should maybe be set to expire after being shown to the user
    a set number of times).
    """
    from django.db import models

    try:
        user = context['request'].user
    except ObjectDoesNotExist:
        user = None

    user_status_code = None

    if user and user.is_authenticated():
        if user.is_community_admin():
            # set code to non-existant status, so that no message is passed to
            # the community admin.
            user_status_code = 'COMMUNITY_ADMIN'
        else:

            if CC3Profile.viewable.is_pending_closure(user):
                user_status_code = 'PEN'

            # 1. check for profile
            if not CC3Profile.viewable.has_completed_profile(user):
                user_status_code = 'NEW'

        # 2. Any ads?
        if user_status_code is None:
            # User must have completed profile, so must have a related CC3
            # profile.
            cc3_profile = CC3Profile.viewable.get(user=user)
            number_of_ads = Ad.objects.filter(created_by=cc3_profile).count()
            if number_of_ads == 0:
                user_status_code = 'NOADS'

            # 3. any transactions
            if user_status_code is None:
                trans = AdPaymentTransaction.objects.filter(
                    models.Q(sender=user) |
                    models.Q(receiver=user)).count()

                if trans == 0:
                    user_status_code = 'NOBUY'

            # 4. any credit?
            if user_status_code is None:
                if not cc3_profile.has_full_account():
                    user_status_code = 'NOCREDIT'

            # 5. ad and purchase?
            if user_status_code is None:
                # In theory they have placed an ad (1.), and they have bought
                # something (3.)
                user_status_code = 'AD_N_BUY'

    user_status_message = user_status_css = user_status_message_obj = None
    user_status_link = user_status_link_text = None
    if user_status_code:
        # try and get the status message (might not have been set up for instance) 
        try:
            user_status_message_obj = StatusMessage.objects.get(
                user_status__code=user_status_code)
            if user_status_message_obj.appearance_limit:
                appearances, created = StatusMessageAppearance.objects.get_or_create(
                    message=user_status_message_obj,
                    user=user, defaults={'count': 1})

                if not created:
                    if appearances.count > user_status_message_obj.appearance_limit:
                        user_status_code = None
                    appearances.count += 1
                    appearances.save()
        except StatusMessage.DoesNotExist:
            pass

    # Check code hasn't been set to None by appearance check or lack of status
    # message in DB.
    if user_status_code and user_status_message_obj:
        user_status_message = user_status_message_obj.get_message()
        user_status_css = user_status_message_obj.status_message_level.css_class
        try:
            user_status_link = reverse(user_status_message_obj.link)
        except:
            user_status_link = ''
        if user_status_link.strip() != '':

            user_status_link_text = user_status_message_obj.get_link_text()
        else:
            user_status_link = None

    return {
        'user_status_message': user_status_message,
        'user_status_css': user_status_css,
        'user_status_link': user_status_link,
        'user_status_link_text': user_status_link_text
    }

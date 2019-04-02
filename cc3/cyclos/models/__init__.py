""" Models for linking to (external) Cyclos application"""
from django.utils.translation import ugettext

from .account import (
    BusinessUserProxyModel, CC3Profile, CyclosAccount, CyclosStatus,
    SYSTEM_USER_IDS, User, is_cc3_member, password_change_signal,
    CardMachineUserProxyModel, get_fullname_signal, UserStatusChangeHistory)
from .group import CyclosGroup, CyclosGroupSet
from .community import CC3Community, CommunityAdmin, CommunityRegistrationCode
from .cms_plugins import CommunityMessage, CommunityPluginModel
from .security import CyclosChannel
from .status_message import (
    StatusMessage, StatusMessageAppearance, StatusMessageLevel,
    StatusMessageTranslation, UserStatus)

# Monkey patch the appropriate admin forms.
# See also:
# http://groups.google.com/group/django-developers/msg/3420dc565df39fb1
from django import forms
from django.contrib.auth.admin import UserAdmin

for form in (UserAdmin.form, UserAdmin.add_form):
    form.declared_fields['username'] = forms.CharField(
        label=ugettext('Username'), max_length=75)

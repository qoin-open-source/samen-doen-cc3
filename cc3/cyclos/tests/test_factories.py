import logging

import factory
from django.conf import settings
from django.contrib.sites.models import Site

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class UserFactory(factory.DjangoModelFactory):
    """
    Factory model for the Django ``User`` model.
    """
    class Meta:
        model = 'cyclos.User'

    first_name = 'Test'
    last_name = 'User'
    username = factory.Sequence(lambda n: 'user_{0}'.format(n))
    email = factory.Sequence(lambda n: 'user_{0}@qoin.org'.format(n))
    password = factory.PostGenerationMethodCall('set_password', 'testing')


class CyclosGroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CyclosGroup'

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: 'Cyclos_group_{0}'.format(n))


class CyclosGroupSetFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CyclosGroupSet'

    name = factory.Sequence(lambda n: 'Cyclos_groupset_{0}'.format(n))
    prefix = factory.Sequence(lambda n: 'PFX_{0}'.format(n))

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for group in extracted:
                self.groups.add(group)


class CC3CommunityFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CC3Community'

    title = factory.Sequence(lambda n: 'Community_{0}'.format(n))

    @factory.post_generation
    def groupsets(self, create, extracted, **kwargs):
        if not create:
            # Create a GroupSet with both an initial and a full Cyclos group
            initial_group = CyclosGroupFactory.create(
                name=u'Initial testgroup', initial=True, full=False)
            full_group = CyclosGroupFactory.create(
                name=u'Full testgroup', initial=False, full=True)
            groupset = CyclosGroupSetFactory.create(
                groups=(initial_group, full_group))
            self.groupsets.add(groupset)

        if extracted:
            # A list of groups were passed in, use them
            for groupset in extracted:
                self.groupsets.add(groupset)


class CommunityAdminFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CommunityAdmin'

    user = factory.SubFactory(UserFactory)
    community = factory.SubFactory(CC3CommunityFactory)


class CommunityRegistrationCodeFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CommunityRegistrationCode'

    code = factory.Sequence(lambda n: 'Code_{0}'.format(n))
    community = factory.SubFactory(CC3CommunityFactory)
    groupset = factory.SubFactory(CyclosGroupSetFactory)


class CMSPlaceholderFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cms.Placeholder'

    slot = factory.Sequence(lambda n: 'Placeholder_{0}'.format(n))


class CMSPageFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cms.Page'

    publisher_is_draft = False
    site = Site.objects.get_current()

    @factory.post_generation
    def placeholders(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for placeholder in extracted:
                self.placeholders.add(placeholder)


class CommunityPluginModelFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CommunityPluginModel'

    body = factory.Sequence(lambda n: 'CommunityPlugin_{0}'.format(n))
    placeholder = factory.Sequence(CMSPlaceholderFactory)


class CommunityMessageFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CommunityMessage'

    plugin = factory.SubFactory(CommunityPluginModelFactory)
    community = factory.SubFactory(CC3CommunityFactory)
    body = factory.Sequence(lambda n: 'CommunityMessage_{0}'.format(n))


class CC3ProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CC3Profile'

    user = factory.SubFactory(UserFactory)
    community = factory.SubFactory(CC3CommunityFactory)
    first_name = factory.Sequence(lambda n: 'CC3Profile_{0}_first'.format(n))
    last_name = factory.Sequence(lambda n: 'CC3Profile_{0}_last'.format(n))
    business_name = factory.Sequence(
        lambda n: 'CC3Profile_{0}_business'.format(n))


class AuthUserProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = getattr(settings, 'AUTH_PROFILE_MODULE', 'cyclos.CC3Profile')

    user = factory.SubFactory(UserFactory)
    community = factory.SubFactory(CC3CommunityFactory)
    first_name = factory.Sequence(lambda n: 'CC3Profile_{0}_first'.format(n))
    last_name = factory.Sequence(lambda n: 'CC3Profile_{0}_last'.format(n))
    business_name = factory.Sequence(
        lambda n: 'CC3Profile_{0}_business'.format(n))


class CyclosAccountFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'cyclos.CyclosAccount'

    cyclos_id = factory.Sequence(lambda n: n)
    cc3_profile = factory.SubFactory(CC3ProfileFactory)


class MailMessageFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'mail.MailMessage'

    subject = "Dummy email subject"
    body = "Dummy email body"

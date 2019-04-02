# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from cc3.marketplace.models import CAMPAIGN_STATUS_CANCELLED
from django.db.models import Q
from datetime import datetime


def make_activity_subscribed_profiles_visible(apps, schema_editor):
    Campaign = apps.get_model("marketplace", "Campaign")
    CampaignParticipant = apps.get_model("marketplace", "CampaignParticipant")
    CC3Profile = apps.get_model("cyclos", "CC3Profile")

    # Get all campaigns that are not cancelled AND that are not finished
    active_campaigns = Campaign.objects.filter(
        ~Q(status=CAMPAIGN_STATUS_CANCELLED),
        start_date__gte=datetime.now().date()).exclude(
        start_date=datetime.now().date(),
        end_time__lte=datetime.now().time())

    # For each campaign in the active campaigns
    for campaign in active_campaigns:
        # Get the list of participants
        participants = CampaignParticipant.objects.filter(campaign=campaign)

        # For each participant
        for p in participants:
            # If the partcipant's profile is already visisble
            if p.profile and not p.profile.is_visible:
                # Get their profile
                profile = CC3Profile.objects.get(id=p.profile.id)
                if profile:
                    profile.is_visible = True
                    profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0003_auto_20160623_1820'),
    ]

    operations = [
        migrations.RunPython(make_activity_subscribed_profiles_visible),
    ]

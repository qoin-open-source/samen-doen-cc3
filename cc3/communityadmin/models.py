from django.db import models
from django.utils import timezone

from ..cyclos.models import CC3Profile


class CommunityMember(models.Model):
    """ READONLY Database view for ease of sorting. """

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    member_email = models.CharField(max_length=75)
    business_name = models.CharField(max_length=255)
    company_website = models.CharField(max_length=255)
    count_offers = models.IntegerField()
    count_wants = models.IntegerField()
    has_full_account = models.BooleanField()
    count_active_ads = models.IntegerField()
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False

    def save(self, **kwargs):
        raise NotImplementedError

    def member(self):
        return CC3Profile.viewable.get(pk=self.id)

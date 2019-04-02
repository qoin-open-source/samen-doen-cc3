from django.core.management.base import BaseCommand, CommandError
from cc3.cyclos.models import User, CC3Profile, CC3Community

class Command(BaseCommand):
    help = 'Create dummy users for testing and dev. NB. Not linked to cyclos'

    def handle(self, *args, **options):
        community = CC3Community.objects.get(title='Qoin')
        for i in range(2, 20):
            user = User.objects.create_user('user%d'%i, 'user%d@mailinator.com'%i, 'password1')
            profile = CC3Profile.objects.create(user=user,
                                        first_name='First %d'%i,
                                        last_name='Last',
                                        country='NL',
                                        community=community,
                                        business_name='Business %d'%i,
                                        slug='business-%d'%i)

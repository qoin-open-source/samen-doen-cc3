# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from cc3.mail.models import MAIL_TYPE_PASSWORD_RESET
from django.db import IntegrityError
import logging

LOG = logging.getLogger(__name__)

def load_password_reset_email_template_3300(apps, schema_editor):
    MailMessage = apps.get_model('mail', 'MailMessage')
    subject = "Wachtwoord reset voor SamenDoen"
    body =  "Beste {{first_name}}{% if middle_initials != None %} {{middle_initials}}{% endif %} {{last_name}}.\n"\
            "Ga naar {{link}} om een nieuw SamenDoen wachtwoord in te stellen.\n"\
            "Geen nieuw wachtwoord aangevraagd? Negeer dan dit bericht.\n"\
            "Met vriendelijke groet,\n"\
            "Team SamenDoen"

    try:
        MailMessage.objects.create(
                            type=MAIL_TYPE_PASSWORD_RESET,
                            subject=subject,
                            body=body,
        )
    except IntegrityError as e:
        LOG.error(e)
        

class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0005_auto_20170307_1901'),
    ]

    operations = [
        migrations.RunPython(load_password_reset_email_template_3300),
    ]

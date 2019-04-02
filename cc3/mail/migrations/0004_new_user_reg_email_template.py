# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from cc3.mail.models import MAIL_TYPE_NEW_REGISTRATION_USER


def load_new_user_reg_email_template_3300(apps, schema_editor):
    MailMessage = apps.get_model('mail', 'MailMessage')
    subject = "Bedankt voor uw aanmelding op Samen Doen!"
    body =  "Bedankt voor je registratie!\n"\
            "Klik op de link om je account te activeren en de spaarpas aan te vragen:\n"\
            "http://{{ site.domain }}{% url 'registration_activate' activation_key %}\n"\
            "(de link is {{expiration_days}} dagen geldig)\n"\
            "Veel spaarplezier!\n"\
            "Team SamenDoen"

    MailMessage.objects.create(
                        type=MAIL_TYPE_NEW_REGISTRATION_USER,
                        subject=subject,
                        body=body,
    )

class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0003_auto_20170306_1737'),
    ]

    operations = [
        migrations.RunPython(load_new_user_reg_email_template_3300),
    ]

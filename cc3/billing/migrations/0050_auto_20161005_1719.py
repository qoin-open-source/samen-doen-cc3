# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0049_auto_20161004_1213'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='auto_assign_type',
            field=models.CharField(blank=True, help_text='Leave blank if assigned manually by admins', max_length=20, verbose_name='Auto-assign type', choices=[(b'TERMINAL_DEPOSIT', 'When terminal assigned to user'), (b'TERMINAL_REFUND', 'When terminal unassigned from user'), (b'TERMINAL_RENTAL', 'To all terminal holders (excl. free ones)'), (b'SIM_CARD', 'To all SIM card holders'), (b'USER_GROUPS', "To all users in product's User Groups")]),
        ),
    ]

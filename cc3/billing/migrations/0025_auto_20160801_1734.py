# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_terminal_deposits(apps, schema_editor):
    # For all currently assigned Terminals, create a TerminalDeposit
    # indicating that the deposit has already been paid
    Terminal = apps.get_model("cards", "Terminal")
    TerminalDeposit = apps.get_model("billing", "TerminalDeposit")
    for terminal in Terminal.objects.filter(business__isnull=False):
        deposit = TerminalDeposit.objects.create(
            terminal=terminal,
            business=terminal.business,
            deposit_due=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0024_auto_20160801_1730'),
    ]

    operations = [
        migrations.RunPython(create_terminal_deposits),
    ]

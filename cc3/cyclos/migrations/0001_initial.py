# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.auth.models
import django_countries.fields
import easy_thumbnails.fields
import cc3.cyclos.utils
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CC3Community',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Community title', unique=True, max_length=255)),
                ('country', django_countries.fields.CountryField(max_length=2, choices=[('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'), ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'), ('AG', 'Antigua and Barbuda'), ('AR', 'Argentina'), ('AM', 'Armenia'), ('AW', 'Aruba'), ('AU', 'Australia'), ('AT', 'Austria'), ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'), ('BY', 'Belarus'), ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'), ('BT', 'Bhutan'), ('BO', 'Bolivia, Plurinational State of'), ('BQ', 'Bonaire, Sint Eustatius and Saba'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('IO', 'British Indian Ocean Territory'), ('BN', 'Brunei Darussalam'), ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'), ('CX', 'Christmas Island'), ('CC', 'Cocos (Keeling) Islands'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('CG', 'Congo'), ('CD', 'Congo (the Democratic Republic of the)'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('HR', 'Croatia'), ('CU', 'Cuba'), ('CW', 'Cura\xe7ao'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('CI', "C\xf4te d'Ivoire"), ('DK', 'Denmark'), ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('EG', 'Egypt'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('ET', 'Ethiopia'), ('FK', 'Falkland Islands  [Malvinas]'), ('FO', 'Faroe Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'), ('GA', 'Gabon'), ('GM', 'Gambia (The)'), ('GE', 'Georgia'), ('DE', 'Germany'), ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'), ('GG', 'Guernsey'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See  [Vatican City State]'), ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran (the Islamic Republic of)'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IM', 'Isle of Man'), ('IL', 'Israel'), ('IT', 'Italy'), ('JM', 'Jamaica'), ('JP', 'Japan'), ('JE', 'Jersey'), ('JO', 'Jordan'), ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'), ('KP', "Korea (the Democratic People's Republic of)"), ('KR', 'Korea (the Republic of)'), ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', "Lao People's Democratic Republic"), ('LV', 'Latvia'), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'), ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), ('MK', 'Macedonia (the former Yugoslav Republic of)'), ('MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('YT', 'Mayotte'), ('MX', 'Mexico'), ('FM', 'Micronesia (the Federated States of)'), ('MD', 'Moldova (the Republic of)'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('ME', 'Montenegro'), ('MS', 'Montserrat'), ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NC', 'New Caledonia'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('MP', 'Northern Mariana Islands'), ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'), ('PS', 'Palestine, State of'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn'), ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'), ('RO', 'Romania'), ('RU', 'Russian Federation'), ('RW', 'Rwanda'), ('RE', 'R\xe9union'), ('BL', 'Saint Barth\xe9lemy'), ('SH', 'Saint Helena, Ascension and Tristan da Cunha'), ('KN', 'Saint Kitts and Nevis'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin (French part)'), ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'), ('SX', 'Sint Maarten (Dutch part)'), ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('GS', 'South Georgia and the South Sandwich Islands'), ('SS', 'South Sudan'), ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard and Jan Mayen'), ('SZ', 'Swaziland'), ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syrian Arab Republic'), ('TW', 'Taiwan (Province of China)'), ('TJ', 'Tajikistan'), ('TZ', 'Tanzania, United Republic of'), ('TH', 'Thailand'), ('TL', 'Timor-Leste'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'), ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'), ('GB', 'United Kingdom'), ('US', 'United States'), ('UM', 'United States Minor Outlying Islands'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VE', 'Venezuela, Bolivarian Republic of'), ('VN', 'Viet Nam'), ('VG', 'Virgin Islands (British)'), ('VI', 'Virgin Islands (U.S.)'), ('WF', 'Wallis and Futuna'), ('EH', 'Western Sahara'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'), ('AX', '\xc5land Islands')])),
                ('community_view', models.CharField(default=1, max_length=1, choices=[(b'1', 'Community members first'), (b'2', 'Only community members'), (b'3', 'No community filter')])),
                ('code', models.CharField(help_text='Used in cyclos, is assigned to each member of this community upon creating the cyclos account. Note that this field should not be confused with "CommunityRegistrationCode", which is a different code for end-users to register with.', max_length=12)),
                ('newreg_notify_cadmin', models.BooleanField(default=True, help_text=b'Notify community administrators when a new user registers', verbose_name='Notify upon registration')),
                ('profilecomplete_notify_cadmin', models.BooleanField(default=True, help_text=b'Notify community administrators when a new user completes their profile', verbose_name='Notify upon completion of profile')),
                ('transcomplete_notify_cadmin', models.BooleanField(default=True, help_text=b'Notify community administrators when a user completes a transaction', verbose_name='Notify upon completion of transactions')),
                ('negative_balance_warning_buffer', models.IntegerField(help_text='Send negative balance warning emails this many days before credit term expires', null=True, verbose_name='Negative balance warning (days)', blank=True)),
                ('negative_balance_collect_after', models.IntegerField(help_text='Send negative balance collection emails this many months after credit term expires', null=True, verbose_name='Negative balance collection after (months)', blank=True)),
                ('newcampaign_notify_members', models.BooleanField(default=False, help_text=b'Email members when a new campaign (activity) is created', verbose_name='Email members about new campaigns')),
            ],
            options={
                'verbose_name': 'community',
                'verbose_name_plural': 'communities',
            },
        ),
        migrations.CreateModel(
            name='CC3Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(default=b'', max_length=255, verbose_name='First name', blank=True)),
                ('last_name', models.CharField(default=b'', max_length=255, verbose_name='Last name', blank=True)),
                ('business_name', models.CharField(default=b'', max_length=255, verbose_name='Business name', blank=True)),
                ('slug', models.SlugField(default=b'', max_length=255, blank=True)),
                ('picture', easy_thumbnails.fields.ThumbnailerImageField(upload_to=cc3.cyclos.utils.get_profile_picture_filename, width_field=b'picture_width', height_field=b'picture_height', blank=True, verbose_name='Picture')),
                ('picture_height', models.IntegerField(verbose_name='Picture height', null=True, editable=False, blank=True)),
                ('picture_width', models.IntegerField(verbose_name='Picture width', null=True, editable=False, blank=True)),
                ('job_title', models.CharField(default=b'', max_length=255, verbose_name='Job title', blank=True)),
                ('country', django_countries.fields.CountryField(max_length=2, verbose_name='Country', choices=[('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'), ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'), ('AG', 'Antigua and Barbuda'), ('AR', 'Argentina'), ('AM', 'Armenia'), ('AW', 'Aruba'), ('AU', 'Australia'), ('AT', 'Austria'), ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'), ('BY', 'Belarus'), ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'), ('BT', 'Bhutan'), ('BO', 'Bolivia, Plurinational State of'), ('BQ', 'Bonaire, Sint Eustatius and Saba'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('IO', 'British Indian Ocean Territory'), ('BN', 'Brunei Darussalam'), ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'), ('CX', 'Christmas Island'), ('CC', 'Cocos (Keeling) Islands'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('CG', 'Congo'), ('CD', 'Congo (the Democratic Republic of the)'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('HR', 'Croatia'), ('CU', 'Cuba'), ('CW', 'Cura\xe7ao'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('CI', "C\xf4te d'Ivoire"), ('DK', 'Denmark'), ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('EG', 'Egypt'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('ET', 'Ethiopia'), ('FK', 'Falkland Islands  [Malvinas]'), ('FO', 'Faroe Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'), ('GA', 'Gabon'), ('GM', 'Gambia (The)'), ('GE', 'Georgia'), ('DE', 'Germany'), ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'), ('GG', 'Guernsey'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See  [Vatican City State]'), ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran (the Islamic Republic of)'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IM', 'Isle of Man'), ('IL', 'Israel'), ('IT', 'Italy'), ('JM', 'Jamaica'), ('JP', 'Japan'), ('JE', 'Jersey'), ('JO', 'Jordan'), ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'), ('KP', "Korea (the Democratic People's Republic of)"), ('KR', 'Korea (the Republic of)'), ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', "Lao People's Democratic Republic"), ('LV', 'Latvia'), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'), ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), ('MK', 'Macedonia (the former Yugoslav Republic of)'), ('MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('YT', 'Mayotte'), ('MX', 'Mexico'), ('FM', 'Micronesia (the Federated States of)'), ('MD', 'Moldova (the Republic of)'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('ME', 'Montenegro'), ('MS', 'Montserrat'), ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NC', 'New Caledonia'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('MP', 'Northern Mariana Islands'), ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'), ('PS', 'Palestine, State of'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn'), ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'), ('RO', 'Romania'), ('RU', 'Russian Federation'), ('RW', 'Rwanda'), ('RE', 'R\xe9union'), ('BL', 'Saint Barth\xe9lemy'), ('SH', 'Saint Helena, Ascension and Tristan da Cunha'), ('KN', 'Saint Kitts and Nevis'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin (French part)'), ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'), ('SX', 'Sint Maarten (Dutch part)'), ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('GS', 'South Georgia and the South Sandwich Islands'), ('SS', 'South Sudan'), ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard and Jan Mayen'), ('SZ', 'Swaziland'), ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syrian Arab Republic'), ('TW', 'Taiwan (Province of China)'), ('TJ', 'Tajikistan'), ('TZ', 'Tanzania, United Republic of'), ('TH', 'Thailand'), ('TL', 'Timor-Leste'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'), ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'), ('GB', 'United Kingdom'), ('US', 'United States'), ('UM', 'United States Minor Outlying Islands'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VE', 'Venezuela, Bolivarian Republic of'), ('VN', 'Viet Nam'), ('VG', 'Virgin Islands (British)'), ('VI', 'Virgin Islands (U.S.)'), ('WF', 'Wallis and Futuna'), ('EH', 'Western Sahara'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'), ('AX', '\xc5land Islands')])),
                ('city', models.CharField(default=b'', max_length=255, verbose_name='City', blank=True)),
                ('address', models.CharField(default=b'', max_length=255, verbose_name='Address', blank=True)),
                ('postal_code', models.CharField(default=b'', max_length=10, verbose_name='Postal code', blank=True)),
                ('registration_number', models.CharField(default=b'', max_length=255, verbose_name='KvK number', blank=True)),
                ('phone_number', models.CharField(default=b'', max_length=255, verbose_name='Phone number', blank=True)),
                ('mobile_number', models.CharField(default=b'', max_length=255, verbose_name='Mobile number', blank=True)),
                ('company_website', models.URLField(default=b'', max_length=255, verbose_name='Company website', blank=True)),
                ('company_description', models.TextField(default=b'', verbose_name='Company description', blank=True)),
                ('must_reset_password', models.BooleanField(default=False, verbose_name='Must reset password')),
                ('is_pending_closure', models.BooleanField(default=False, verbose_name='Is pending closure')),
                ('date_closure_requested', models.DateTimeField(null=True, verbose_name='Date closure requested', blank=True)),
                ('is_visible', models.BooleanField(default=True, help_text='Marking as visible shows the profile to be shown on the marketplace', verbose_name='Is visible')),
                ('is_approved', models.BooleanField(default=True, help_text='Approving profile will automatically make it visible; unapproving will make it invisible', verbose_name='Profile approved')),
                ('has_received_activation_invoice', models.BooleanField(default=False, verbose_name='Has received activation invoice')),
                ('has_notified_profilecomplete', models.BooleanField(default=False, verbose_name='Has notified profile complete')),
                ('email_category_matches', models.BooleanField(default=True, verbose_name='Notify me of new matches')),
                ('email_new_campaigns', models.BooleanField(default=True, verbose_name='Notify me about new activities')),
                ('credit_term', models.IntegerField(default=4, null=True, verbose_name='Credit term (months)', blank=True)),
                ('negative_balance_start_date', models.DateField(null=True, verbose_name='Date balance went negative', blank=True)),
                ('negative_balance_warning_sent', models.DateField(null=True, verbose_name='Date negative balance warning was sent', blank=True)),
                ('negative_balance_collect_sent', models.DateField(null=True, verbose_name='Date negative balance collection email was sent', blank=True)),
                ('large_balance_start_date', models.DateField(null=True, verbose_name='Date balance exceeded limit', blank=True)),
                ('web_payments_enabled', models.BooleanField(default=True, help_text='Allow user to make payments in the marketplace')),
                ('latitude', models.DecimalField(null=True, max_digits=17, decimal_places=14, blank=True)),
                ('longitude', models.DecimalField(null=True, max_digits=17, decimal_places=14, blank=True)),
                ('map_zoom', models.IntegerField(null=True, blank=True)),
                ('first_login', models.NullBooleanField(help_text='Is this the first time a user has logged in? (Defaults to true in save method)')),
                ('categories', models.ManyToManyField(to='core.Category', blank=True)),
                ('community', models.ForeignKey(blank=True, to='cyclos.CC3Community', null=True)),
            ],
            options={
                'verbose_name': 'profile',
                'verbose_name_plural': 'profiles',
            },
        ),
        migrations.CreateModel(
            name='CommunityAdmin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_default', models.BooleanField(default=False)),
                ('community', models.ForeignKey(to='cyclos.CC3Community')),
            ],
        ),
        migrations.CreateModel(
            name='CommunityRegistrationCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=10)),
                ('community', models.ForeignKey(to='cyclos.CC3Community')),
            ],
            options={
                'verbose_name': 'community registration code',
            },
        ),
        migrations.CreateModel(
            name='CyclosAccount',
            fields=[
                ('cyclos_id', models.IntegerField(serialize=False, verbose_name='Cyclos account ID', primary_key=True)),
                ('cyclos_group', models.SmallIntegerField(help_text='Cyclos backend group ID.', null=True, verbose_name='Cyclos Group ID', blank=True)),
                ('cc3_profile', models.OneToOneField(related_name='cyclos_account', verbose_name='cc3 profile', to='cyclos.CC3Profile')),
            ],
            options={
                'ordering': ('cc3_profile__user__username',),
            },
        ),
        migrations.CreateModel(
            name='CyclosChannel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False, db_index=True)),
                ('internal_name', models.CharField(help_text='Used to identify channel in Cyclos. Must be the same as the internal name in Cyclos', max_length=50)),
                ('display_name', models.CharField(help_text='Displayed to user on their security screen (can be the same as the display name in Cyclos)', max_length=100)),
                ('is_web_channel', models.BooleanField(default=False, help_text='Identify web channel, which is only disabled on the Django side')),
                ('image', easy_thumbnails.fields.ThumbnailerImageField(height_field=b'height', width_field=b'width', upload_to=cc3.cyclos.utils.get_cyclos_channel_image_filename, blank=True)),
            ],
            options={
                'ordering': ('order', 'display_name'),
                'verbose_name_plural': 'channels',
            },
        ),
        migrations.CreateModel(
            name='CyclosGroup',
            fields=[
                ('id', models.IntegerField(help_text=b'ID of a CyclosGroup must be the same as an existing group in Cyclos, this field is not auto-incremented', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('permit_split_payments_in_euros', models.BooleanField(default=False, help_text=b'Split payments, specifically for the BYB group (implemented)')),
                ('initial', models.BooleanField(default=False, help_text=b'This is the group to use when a member self-registers (implemented)')),
                ('trial', models.BooleanField(default=False, help_text=b'This group has no joining fee but may have restricted functionality (not implemented)')),
                ('full', models.BooleanField(default=True, help_text=b'This group does not have restricted functionality (implemented)')),
                ('paid', models.BooleanField(default=False, help_text=b'Members cannot be moved to this group without a fee being paid or invoiced (not implemented)')),
                ('inactive', models.BooleanField(default=False, help_text=b'A group that members are moved to when they have left the scheme, members in this group will not be shown publicly or be able to log in, so the auth_user is_active flag should be disabled as well (not implemented)')),
                ('send_notification', models.BooleanField(default=False, help_text=b'Send a notification when a community admin changes a user to this group')),
                ('visible_to_all_communities', models.BooleanField(default=False, help_text=b'If true, profiles with this cyclos group set should be visible to all communities')),
                ('create_monthly_invoice', models.BooleanField(default=False, help_text='Automatically create a monthly invoice for these users. Note: ensure that users in the groupset may view invoices.')),
                ('create_activation_invoice', models.BooleanField(default=False, help_text='Automatically create an invoice upon activation of a user')),
                ('invoice_day_otm', models.IntegerField(default=1, help_text='Day of the month that automatic monthly invoices are sent', verbose_name=b'Invoice day of the month')),
                ('invoice_monthly_amount', models.DecimalField(help_text='Amount to be automatically invoiced each month. If not specified AUTO_INVOICE_AMOUNT will be used from the project settings to determine this value', null=True, max_digits=12, decimal_places=4, blank=True)),
                ('invoice_monthly_description', models.CharField(help_text='Description added to the invoice about the monthly payment', max_length=255, blank=True)),
                ('invoice_activation_amount', models.DecimalField(help_text='Amount to be automatically invoiced upon activation. If not specified AUTO_INVOICE_AMOUNT will be used from the project settings to determine this value', null=True, max_digits=12, decimal_places=4, blank=True)),
                ('invoice_activation_description', models.CharField(help_text='Description added to the invoice about the activation payment', max_length=255, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='CyclosGroupSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('prefix', models.CharField(help_text='If provided, the account number is prefixed with the value in this field', unique=True, max_length=10, blank=True)),
                ('slug', models.SlugField(help_text="Used to identify this groupset in project-specific views and templates. For SoNantes, set this to 'company' or 'individual'", blank=True)),
                ('is_visible', models.BooleanField(default=True, help_text='If the profiles with this groupset are visible in the marketplace business-view')),
                ('may_add_ads', models.BooleanField(default=True, help_text='If the users within this groupset may add ads via the account side-menu')),
                ('may_view_invoices', models.BooleanField(default=True, help_text='If the users within this groupset may view their invoices via the account side-menu')),
                ('is_business', models.BooleanField(default=False, help_text='If the users within this groupset may be linked with terminals and create operators for dealing with card transactions')),
                ('groups', models.ManyToManyField(related_name='groupsets', to='cyclos.CyclosGroup', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='CyclosStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(default=b'', max_length=5, blank=True)),
                ('description', models.CharField(default=b'', max_length=255, blank=True)),
            ],
            options={
                'verbose_name_plural': 'cyclos statuses',
            },
        ),
        migrations.CreateModel(
            name='StatusMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Default title', max_length=50)),
                ('message', models.CharField(help_text='Default message, shown to user', max_length=255)),
                ('link', models.CharField(default=b'', help_text='Reverse ID of page to link to (ask a system administrator!)', max_length=255, blank=True)),
                ('link_text', models.CharField(default=b'', help_text='Text for link', max_length=255, blank=True)),
                ('appearance_limit', models.IntegerField(help_text='Number of times a message should appear to a user (optional).', null=True, blank=True)),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name_plural': 'status messages',
            },
        ),
        migrations.CreateModel(
            name='StatusMessageAppearance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('count', models.IntegerField(default=0)),
                ('message', models.ForeignKey(to='cyclos.StatusMessage')),
            ],
        ),
        migrations.CreateModel(
            name='StatusMessageLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('css_class', models.CharField(max_length=15)),
                ('description', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='StatusMessageTranslation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Status Message title', max_length=50)),
                ('message', models.CharField(help_text='Status message', max_length=255)),
                ('link_text', models.CharField(default=b'', help_text='Text for link', max_length=255, blank=True)),
                ('language', models.CharField(max_length=5, choices=[(b'nl', b'Dutch')])),
                ('status_message', models.ForeignKey(blank=True, to='cyclos.StatusMessage', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(help_text=b'User status code, used in code to identify', max_length=10)),
                ('description', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name_plural': 'user statuses',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='userstatus',
            unique_together=set([('code', 'description')]),
        ),
        migrations.AddField(
            model_name='statusmessageappearance',
            name='user',
            field=models.ForeignKey(to='cyclos.User'),
        ),
        migrations.AddField(
            model_name='statusmessage',
            name='status_message_level',
            field=models.ForeignKey(to='cyclos.StatusMessageLevel'),
        ),
        migrations.AddField(
            model_name='statusmessage',
            name='user_status',
            field=models.ForeignKey(to='cyclos.UserStatus'),
        ),
        migrations.AddField(
            model_name='cyclosgroup',
            name='invoice_user',
            field=models.ForeignKey(blank=True, to='cyclos.User', help_text='The user from which automatic invoices are sent. Mandatory if "create monthly invoice" is enabled.', null=True, verbose_name='Invoice sender'),
        ),
        migrations.AddField(
            model_name='communityregistrationcode',
            name='groupset',
            field=models.ForeignKey(blank=True, to='cyclos.CyclosGroupSet', null=True),
        ),
        migrations.AddField(
            model_name='communityadmin',
            name='user',
            field=models.OneToOneField(related_name='administrator_of', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cc3profile',
            name='cyclos_group',
            field=models.ForeignKey(blank=True, to='cyclos.CyclosGroup', null=True),
        ),
        migrations.AddField(
            model_name='cc3profile',
            name='groupset',
            field=models.ForeignKey(blank=True, to='cyclos.CyclosGroupSet', null=True),
        ),
        migrations.AddField(
            model_name='cc3profile',
            name='user',
            field=models.OneToOneField(related_name='cc3_profile', verbose_name='user', to='cyclos.User'),
        ),
        migrations.AddField(
            model_name='cc3profile',
            name='want_categories',
            field=models.ManyToManyField(related_name='cc3profile_wanting', to='core.Category', blank=True),
        ),
        migrations.AddField(
            model_name='cc3community',
            name='groupsets',
            field=models.ManyToManyField(related_name='communities', to='cyclos.CyclosGroupSet', blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='statusmessagetranslation',
            unique_together=set([('language', 'status_message')]),
        ),
        migrations.AlterUniqueTogether(
            name='statusmessageappearance',
            unique_together=set([('message', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='statusmessage',
            unique_together=set([('user_status', 'title')]),
        ),
        migrations.AlterUniqueTogether(
            name='communityregistrationcode',
            unique_together=set([('community', 'groupset')]),
        ),
    ]

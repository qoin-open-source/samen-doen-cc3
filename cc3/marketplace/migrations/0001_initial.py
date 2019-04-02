# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cc3.marketplace.utils
import django_countries.fields
import easy_thumbnails.fields
import adminsortable.fields
import tinymce.models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        ('core', '0002_auto_20160609_1608'),
        ('cyclos', '0003_auto_20160609_1610'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ad',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Title of the offer/want', max_length=255, verbose_name='Title')),
                ('description', tinymce.models.HTMLField(verbose_name='Description')),
                ('price', models.DecimalField(null=True, verbose_name='Price', max_digits=10, decimal_places=2, blank=True)),
                ('barter_euros', models.DecimalField(null=True, verbose_name='Barter euros', max_digits=10, decimal_places=2, blank=True)),
                ('views', models.IntegerField(default=0, verbose_name='Views')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name=b'Date created')),
                ('status', models.CharField(default=b'active', help_text='Only community administrators may change "on hold" ads', max_length=50, choices=[(b'active', 'Enabled'), (b'disabled', 'Disabled'), (b'onhold', 'On hold')])),
            ],
        ),
        migrations.CreateModel(
            name='AdImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name=b'Date created')),
                ('caption', models.CharField(help_text='A caption to be displayed or used as alt text', max_length=200, null=True, blank=True)),
                ('height', models.IntegerField(null=True, editable=False, blank=True)),
                ('width', models.IntegerField(null=True, editable=False, blank=True)),
                ('url', models.URLField(null=True, editable=False, blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Not currently in use, but could hide images when unticked if implemented', editable=False)),
                ('order', models.IntegerField(default=0, help_text='Not currently in use', editable=False)),
                ('image', easy_thumbnails.fields.ThumbnailerImageField(height_field=b'height', width_field=b'width', upload_to=cc3.marketplace.utils.get_ad_image_filename, blank=True)),
                ('ad', models.ForeignKey(blank=True, to='marketplace.Ad', null=True)),
                ('user_created', models.ForeignKey(blank=True, editable=False, to='cyclos.User', null=True, verbose_name='Created by')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='AdPaymentTransaction',
            fields=[
                ('transaction_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.Transaction')),
                ('title', models.CharField(max_length=255)),
                ('split_payment_total_amount', models.DecimalField(help_text='Total amount, in case of BYB/split-currency payments', null=True, max_digits=10, decimal_places=2, blank=True)),
                ('ad', models.ForeignKey(blank=True, to='marketplace.Ad', help_text='Ad related to payment or None if direct payment', null=True)),
            ],
            bases=('core.transaction',),
        ),
        migrations.CreateModel(
            name='AdPricingOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Pricing option', max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='AdPricingOptionTranslation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Pricing option', max_length=50)),
                ('language', models.CharField(max_length=5, choices=[(b'nl', b'Dutch')])),
                ('ad_pricing_option', models.ForeignKey(to='marketplace.AdPricingOption')),
            ],
            options={
                'ordering': ['ad_pricing_option', 'language'],
            },
        ),
        migrations.CreateModel(
            name='AdType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=4)),
                ('title', models.CharField(help_text='Offer or Want in MVP - to be translated?', max_length=50, choices=[(b'O', 'Offer'), (b'W', 'Want')])),
                ('active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('country', django_countries.fields.CountryField(default=b'', max_length=2, verbose_name='Country', blank=True, choices=[('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'), ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'), ('AG', 'Antigua and Barbuda'), ('AR', 'Argentina'), ('AM', 'Armenia'), ('AW', 'Aruba'), ('AU', 'Australia'), ('AT', 'Austria'), ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'), ('BY', 'Belarus'), ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'), ('BT', 'Bhutan'), ('BO', 'Bolivia, Plurinational State of'), ('BQ', 'Bonaire, Sint Eustatius and Saba'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('IO', 'British Indian Ocean Territory'), ('BN', 'Brunei Darussalam'), ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'), ('CX', 'Christmas Island'), ('CC', 'Cocos (Keeling) Islands'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('CG', 'Congo'), ('CD', 'Congo (the Democratic Republic of the)'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('HR', 'Croatia'), ('CU', 'Cuba'), ('CW', 'Cura\xe7ao'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('CI', "C\xf4te d'Ivoire"), ('DK', 'Denmark'), ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('EG', 'Egypt'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('ET', 'Ethiopia'), ('FK', 'Falkland Islands  [Malvinas]'), ('FO', 'Faroe Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'), ('GA', 'Gabon'), ('GM', 'Gambia (The)'), ('GE', 'Georgia'), ('DE', 'Germany'), ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'), ('GG', 'Guernsey'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See  [Vatican City State]'), ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran (the Islamic Republic of)'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IM', 'Isle of Man'), ('IL', 'Israel'), ('IT', 'Italy'), ('JM', 'Jamaica'), ('JP', 'Japan'), ('JE', 'Jersey'), ('JO', 'Jordan'), ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'), ('KP', "Korea (the Democratic People's Republic of)"), ('KR', 'Korea (the Republic of)'), ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', "Lao People's Democratic Republic"), ('LV', 'Latvia'), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'), ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), ('MK', 'Macedonia (the former Yugoslav Republic of)'), ('MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('YT', 'Mayotte'), ('MX', 'Mexico'), ('FM', 'Micronesia (the Federated States of)'), ('MD', 'Moldova (the Republic of)'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('ME', 'Montenegro'), ('MS', 'Montserrat'), ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NC', 'New Caledonia'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('MP', 'Northern Mariana Islands'), ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'), ('PS', 'Palestine, State of'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn'), ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'), ('RO', 'Romania'), ('RU', 'Russian Federation'), ('RW', 'Rwanda'), ('RE', 'R\xe9union'), ('BL', 'Saint Barth\xe9lemy'), ('SH', 'Saint Helena, Ascension and Tristan da Cunha'), ('KN', 'Saint Kitts and Nevis'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin (French part)'), ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'), ('SX', 'Sint Maarten (Dutch part)'), ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('GS', 'South Georgia and the South Sandwich Islands'), ('SS', 'South Sudan'), ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard and Jan Mayen'), ('SZ', 'Swaziland'), ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syrian Arab Republic'), ('TW', 'Taiwan (Province of China)'), ('TJ', 'Tajikistan'), ('TZ', 'Tanzania, United Republic of'), ('TH', 'Thailand'), ('TL', 'Timor-Leste'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'), ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'), ('GB', 'United Kingdom'), ('US', 'United States'), ('UM', 'United States Minor Outlying Islands'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VE', 'Venezuela, Bolivarian Republic of'), ('VN', 'Viet Nam'), ('VG', 'Virgin Islands (British)'), ('VI', 'Virgin Islands (U.S.)'), ('WF', 'Wallis and Futuna'), ('EH', 'Western Sahara'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'), ('AX', '\xc5land Islands')])),
                ('city', models.CharField(default=b'', max_length=255, verbose_name='City', blank=True)),
                ('num_street', models.CharField(default=b'', max_length=50, blank=True)),
                ('address', models.CharField(default=b'', max_length=255, verbose_name='Address', blank=True)),
                ('extra_address', models.CharField(default=b'', max_length=255, blank=True)),
                ('postal_code', models.CharField(default=b'', max_length=10, verbose_name='Postal code', blank=True)),
                ('latitude', models.DecimalField(null=True, max_digits=17, decimal_places=14, blank=True)),
                ('longitude', models.DecimalField(null=True, max_digits=17, decimal_places=14, blank=True)),
                ('map_zoom', models.IntegerField(null=True, blank=True)),
                ('title', models.CharField(help_text='Title of the activity', max_length=60, verbose_name='Title')),
                ('description', tinymce.models.HTMLField(verbose_name='Description of the activity')),
                ('image', easy_thumbnails.fields.ThumbnailerImageField(default=b'', height_field=b'image_height', width_field=b'image_width', upload_to=cc3.marketplace.utils.get_campaign_image_filename, blank=True, verbose_name='Image')),
                ('image_height', models.IntegerField(verbose_name='Image height', null=True, editable=False, blank=True)),
                ('image_width', models.IntegerField(verbose_name='Image width', null=True, editable=False, blank=True)),
                ('criteria', models.CharField(max_length=100, verbose_name='Criteria for participants', blank=True)),
                ('start_date', models.DateField(verbose_name='Date of activity')),
                ('start_time', models.TimeField(verbose_name='Start time')),
                ('end_time', models.TimeField(verbose_name='End time')),
                ('max_participants', models.IntegerField(verbose_name='Number of participants needed')),
                ('reward_per_participant', models.DecimalField(verbose_name='Reward per participant', max_digits=10, decimal_places=2)),
                ('contact_name', models.CharField(max_length=100, verbose_name='Contact name')),
                ('contact_telephone', models.CharField(max_length=100, verbose_name='Contact telephone number', blank=True)),
                ('contact_email', models.EmailField(max_length=100, verbose_name='Contact email')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name=b'Date created')),
                ('status', models.CharField(default=b'V', max_length=1, choices=[(b'V', 'Published'), (b'H', 'Not published'), (b'C', 'Cancelled')])),
                ('why_cancelled', models.TextField(verbose_name='Reason for cancellation (if cancelled)', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CampaignCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False, db_index=True)),
                ('title', models.CharField(help_text='Category title', max_length=100)),
                ('description', models.CharField(help_text='Category description', max_length=255)),
                ('active', models.BooleanField(default=True, help_text='Marks this Category as active')),
                ('parent', adminsortable.fields.SortableForeignKey(related_name='children', blank=True, to='marketplace.CampaignCategory', null=True)),
            ],
            options={
                'ordering': ('order', 'title'),
                'abstract': False,
                'verbose_name_plural': 'categories',
            },
        ),
        migrations.CreateModel(
            name='CampaignCategoryTranslation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='Category title', max_length=50)),
                ('description', models.CharField(max_length=255)),
                ('language', models.CharField(max_length=5, choices=[(b'nl', b'Dutch')])),
                ('category', models.ForeignKey(related_name='translations', blank=True, to='marketplace.CampaignCategory', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CampaignParticipant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('start_time', models.TimeField(null=True, verbose_name='Start time', blank=True)),
                ('end_time', models.TimeField(null=True, verbose_name='End time', blank=True)),
                ('date_rewarded', models.DateTimeField(null=True, blank=True)),
                ('reward_amount', models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True)),
                ('campaign', models.ForeignKey(related_name='participants', to='marketplace.Campaign')),
                ('profile', models.ForeignKey(related_name='campaigns', to='cyclos.CC3Profile')),
            ],
        ),
        migrations.CreateModel(
            name='PreAdImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name=b'Date created')),
                ('caption', models.CharField(help_text='A caption to be displayed or used as alt text', max_length=200, null=True, blank=True)),
                ('height', models.IntegerField(null=True, editable=False, blank=True)),
                ('width', models.IntegerField(null=True, editable=False, blank=True)),
                ('url', models.URLField(null=True, editable=False, blank=True)),
                ('image', easy_thumbnails.fields.ThumbnailerImageField(height_field=b'height', width_field=b'width', upload_to=b'ad_images_p', blank=True)),
                ('user_created', models.ForeignKey(blank=True, editable=False, to='cyclos.User', null=True, verbose_name='Created by')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='campaign',
            name='categories',
            field=models.ManyToManyField(to='marketplace.CampaignCategory', verbose_name='Categories'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='communities',
            field=models.ManyToManyField(to='cyclos.CC3Community', verbose_name='Participating communities'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='created_by',
            field=models.ForeignKey(to='cyclos.CC3Profile'),
        ),
        migrations.AddField(
            model_name='ad',
            name='adtype',
            field=models.ForeignKey(default=1, verbose_name='Offer or want', to='marketplace.AdType'),
        ),
        migrations.AddField(
            model_name='ad',
            name='category',
            field=models.ManyToManyField(to='core.Category', verbose_name='Categories'),
        ),
        migrations.AddField(
            model_name='ad',
            name='created_by',
            field=models.ForeignKey(to='cyclos.CC3Profile'),
        ),
        migrations.AddField(
            model_name='ad',
            name='keywords',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Keywords'),
        ),
        migrations.AddField(
            model_name='ad',
            name='price_option',
            field=models.ForeignKey(verbose_name='Other pricing option', blank=True, to='marketplace.AdPricingOption', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='campaigncategorytranslation',
            unique_together=set([('language', 'category')]),
        ),
        migrations.AlterUniqueTogether(
            name='adpricingoptiontranslation',
            unique_together=set([('language', 'ad_pricing_option')]),
        ),
    ]

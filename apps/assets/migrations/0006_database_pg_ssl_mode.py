# Generated by Django 4.1.13 on 2024-09-13 08:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0005_myasset'),
    ]

    operations = [
        migrations.AddField(
            model_name='database',
            name='pg_ssl_mode',
            field=models.CharField(choices=[
                ('prefer', 'Prefer'),
                ('require', 'Require'),
                ('verify-ca', 'Verify CA'),
                ('verify-full', 'Verify Full')
            ], default='prefer',
                max_length=16, verbose_name='Postgresql SSL mode'),
        ),
    ]

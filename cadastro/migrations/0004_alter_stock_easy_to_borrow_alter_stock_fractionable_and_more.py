# Generated by Django 4.1.3 on 2022-11-06 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0003_rename_crypto_stock_class_alpaca_stock_origin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stock',
            name='easy_to_borrow',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name='stock',
            name='fractionable',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name='stock',
            name='marginable',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name='stock',
            name='shortable',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name='stock',
            name='tradable',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
    ]

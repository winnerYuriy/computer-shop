from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0008_adminnotification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='old_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Поточна ціна зі знижкою; звичайна ціна задається в полі «Ціна».',
                max_digits=12,
                null=True,
                verbose_name='Акційна ціна',
            ),
        ),
    ]
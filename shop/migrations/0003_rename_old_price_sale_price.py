from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0002_product_rating_product_reviews_count_review'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='old_price',
            new_name='sale_price',
        ),
        migrations.AlterField(
            model_name='product',
            name='sale_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Поточна ціна зі знижкою. Звичайна ціна задається в полі «Ціна».',
                max_digits=10,
                null=True,
                verbose_name='Акційна ціна',
            ),
        ),
    ]
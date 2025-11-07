from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("scanner", "0005_add_fcf_fields"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="curatedstock",
            index=models.Index(
                fields=["last_calculation_date"],
                name="scanner_curated_stock_calc_date_idx",
            ),
        ),
    ]

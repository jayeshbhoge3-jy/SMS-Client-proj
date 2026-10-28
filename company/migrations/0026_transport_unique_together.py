from django.db import migrations, models


def rename_duplicate_vehicle_numbers(apps, schema_editor):
    """
    For each (company, vehicle_number) group with more than one row,
    keep the first row's vehicle_number unchanged and append -2, -3, ...
    to the remaining duplicates so the unique constraint can be applied.
    """
    Transport = apps.get_model('company', 'Transport')

    from collections import defaultdict
    groups = defaultdict(list)

    for t in Transport.objects.order_by('id').only(
        'id', 'company_id', 'vehicle_number'
    ):
        groups[(t.company_id, t.vehicle_number)].append(t.id)

    for (company_id, vehicle_number), ids in groups.items():
        if len(ids) <= 1:
            continue

        # keep the first (lowest id) as-is, rename the rest
        for index, transport_id in enumerate(ids[1:], start=2):
            new_number = f"{vehicle_number}-{index}"

            # ensure the new value doesn't itself collide
            while Transport.objects.filter(
                company_id=company_id, vehicle_number=new_number
            ).exclude(id=transport_id).exists():
                index += 1
                new_number = f"{vehicle_number}-{index}"

            Transport.objects.filter(id=transport_id).update(
                vehicle_number=new_number
            )


def reverse_noop(apps, schema_editor):
    # No automatic way to restore original duplicate values; no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0025_company_is_active_company_last_login'),
    ]

    operations = [
        migrations.RunPython(
            rename_duplicate_vehicle_numbers,
            reverse_code=reverse_noop,
        ),
        migrations.AlterField(
            model_name='transport',
            name='vehicle_number',
            field=models.CharField(max_length=30),
        ),
        migrations.AlterUniqueTogether(
            name='transport',
            unique_together={('company', 'vehicle_number')},
        ),
    ]

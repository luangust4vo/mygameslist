from django.db import migrations


def create_moderador_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Moderador")


def delete_moderador_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Moderador").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("games", "0003_game_description_pt"),
    ]

    operations = [
        migrations.RunPython(create_moderador_group, delete_moderador_group),
    ]

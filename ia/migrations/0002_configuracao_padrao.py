from django.db import migrations


def criar_configuracao(apps, schema_editor):
    ConfiguracaoIA = apps.get_model("ia", "ConfiguracaoIA")
    ConfiguracaoIA.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [
        ("ia", "0001_inicial"),
    ]

    operations = [
        migrations.RunPython(criar_configuracao, migrations.RunPython.noop),
    ]

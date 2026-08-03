from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0007_practicesession'),
    ]

    operations = [
        migrations.AddField(
            model_name='quizgenerationrecord',
            name='item_progress',
            field=models.JSONField(blank=True, default=dict, verbose_name='题级作答进度'),
        ),
        migrations.AddField(
            model_name='quizgenerationrecord',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='激活中'),
        ),
        migrations.AddField(
            model_name='quizgenerationrecord',
            name='source',
            field=models.CharField(default='normal', max_length=16, verbose_name='来源'),
        ),
    ]

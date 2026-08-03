from django.apps import AppConfig


class PlanConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plan"
    verbose_name = "学习计划"

    def ready(self):
        # 注册 post_save 信号 → 新建 Subject 时自动生成基础计划
        from . import signals  # noqa: F401
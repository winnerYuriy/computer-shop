from django.contrib.admin.apps import AdminConfig


class TechShopAdminConfig(AdminConfig):
    default_site = 'admin_config.admin_site.TechShopAdminSite'

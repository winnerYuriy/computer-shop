from django.contrib.admin import AdminSite


class TechShopAdminSite(AdminSite):
    site_header = 'TechShop Адміністрування'
    site_title = 'TechShop Admin'
    index_title = 'Панель керування магазином'


admin_site = TechShopAdminSite(name='myadmin')
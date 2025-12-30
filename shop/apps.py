from django.apps import AppConfig

class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        # This print statement will prove if the app is loading
        print("------------------------------------------")
        print("✅ SHOP SIGNALS LOADED SUCCESSFULLY")
        print("------------------------------------------")
        import shop.signals
from django.contrib import admin
from tracker.models import Account, Campaign, Transaction

# Register your models here.
admin.site.register(Account)
admin.site.register(Campaign)
admin.site.register(Transaction)

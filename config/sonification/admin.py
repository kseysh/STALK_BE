from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Stock)
admin.site.register(Record)
admin.site.register(UserStock)

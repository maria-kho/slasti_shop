from django.contrib import admin
from .models import Courier, Order


class OrderInline(admin.TabularInline):
    model = Order
    fields = ['order_id', 'weight', 'complete_time']
    readonly_fields = ('order_id', 'weight', 'complete_time')


class CourierAdmin(admin.ModelAdmin):
    inlines = [
        OrderInline
    ]


admin.site.register(Courier, CourierAdmin)
admin.site.register(Order)

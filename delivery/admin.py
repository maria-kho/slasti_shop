from django.contrib import admin
from .models import Courier, Order, Batch


class OrderInline(admin.TabularInline):
    model = Order
    fields = ['order_id', 'weight', 'complete_time', 'region']
    readonly_fields = ('order_id', 'weight', 'complete_time', 'region')


class BatchInline(admin.TabularInline):
    model = Batch
    fk_name = 'current_courier'
    fields = ['assign_time', 'assign_type']


class CourierAdmin(admin.ModelAdmin):
    inlines = [BatchInline]


class BatchAdmin(admin.ModelAdmin):
    inlines = [OrderInline]


admin.site.register(Courier, CourierAdmin)
admin.site.register(Order)
admin.site.register(Batch, BatchAdmin)

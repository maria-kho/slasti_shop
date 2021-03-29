from django.db import models
from django.db.models import Sum

from delivery.consts import COURIER_TYPES, COURIER_CAPACITIES


class Courier(models.Model):
    courier_id = models.PositiveIntegerField(primary_key=True)
    courier_type = models.CharField(choices=COURIER_TYPES, max_length=5)
    regions = models.JSONField()
    working_hours = models.JSONField()
    assign_time = models.DateTimeField(null=True, blank=True)

    @property
    def capacity(self):
        return COURIER_CAPACITIES[self.courier_type]

    @property
    def total_weight(self):
        return Order.objects.filter(
            courier_id=self.courier_id, complete_time__isnull=True
        ).aggregate(Sum('weight'))['weight__sum'] or 0


class Order(models.Model):
    order_id = models.PositiveIntegerField(primary_key=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2)
    region = models.PositiveIntegerField()
    delivery_hours = models.JSONField()
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, null=True, blank=True, related_name='orders')
    complete_time = models.DateTimeField(null=True, blank=True)

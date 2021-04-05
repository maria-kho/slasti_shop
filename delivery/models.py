from django.db import models
from django.db.models import Sum

from delivery.consts import COURIER_TYPES, COURIER_CAPACITIES


class Courier(models.Model):
    courier_id = models.PositiveIntegerField(primary_key=True)
    courier_type = models.CharField(choices=COURIER_TYPES, max_length=5)
    regions = models.JSONField()
    working_hours = models.JSONField()

    @property
    def capacity(self):
        return COURIER_CAPACITIES[self.courier_type]

    @property
    def total_weight(self):
        return Order.objects.filter(
            batch__current_courier=self, complete_time__isnull=True
        ).aggregate(Sum('weight'))['weight__sum'] or 0


class Batch(models.Model):
    past_courier = models.ForeignKey(
        Courier, on_delete=models.CASCADE, null=True, blank=True, related_name='past_batches'
    )
    current_courier = models.OneToOneField(
        Courier, on_delete=models.CASCADE, null=True, blank=True, related_name='current_batch'
    )
    assign_time = models.DateTimeField()
    assign_type = models.CharField(choices=COURIER_TYPES, max_length=5)

    class Meta:
        verbose_name_plural = 'Batches'


class Order(models.Model):
    order_id = models.PositiveIntegerField(primary_key=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2)
    region = models.PositiveIntegerField()
    delivery_hours = models.JSONField()
    complete_time = models.DateTimeField(null=True, blank=True)
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.CASCADE, related_name='orders')

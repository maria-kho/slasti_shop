from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Courier, Order
from rest_framework import serializers


def has_intersection(time_ranges_1, time_ranges_2):
    for i in time_ranges_1:
        for j in time_ranges_2:
            start1, end1 = j.split('-')
            start2, end2 = i.split('-')
            if start1 < end2 and end1 > start2:
                return True
    return False


class CourierSerializer(serializers.ModelSerializer):
    regions = serializers.ListField(child=serializers.IntegerField(min_value=1))

    def update(self, instance, validated_data):
        super().update(instance, validated_data)

        # drop orders with non-matching regions
        orders_to_drop = Order.objects.filter(
            courier_id=instance.courier_id, complete_time__isnull=True
        ).exclude(region__in=instance.regions)
        orders_to_drop.update(courier=None)

        # drop orders with non-matching schedule
        orders = Order.objects.filter(
            courier_id=instance.courier_id, complete_time__isnull=True
        ).order_by('-weight')
        for order in orders:
            if not has_intersection(order.delivery_hours, instance.working_hours):
                order.courier = None
                order.save()

        # is the weight still ok?
        orders.update()
        total_weight = instance.total_weight
        capacity = instance.capacity
        if capacity > total_weight:
            return instance

        # drop orders that are too heavy
        for order in orders:
            order.courier = None
            order.save()
            if capacity >= instance.total_weight:
                break

        return instance

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions', 'working_hours']


class CourierShortSerializer(CourierSerializer):
    def validate(self, data):
        courier_id = data.get('courier_id')
        if hasattr(self, 'initial_data'):
            initial_index = next(
                (index for (index, d) in enumerate(self.initial_data) if d["courier_id"] == courier_id), None
            )
            unknown_keys = set(self.initial_data[initial_index].keys()) - set(self.fields.keys())
            if unknown_keys:
                raise ValidationError(detail=f'Got unknown fields: {unknown_keys} for courier_id {courier_id}')
        return data

    def to_representation(self, instance):
        return {'id': instance.courier_id}


class OrderSerializer(serializers.ModelSerializer):
    weight = serializers.DecimalField(min_value=0.005, max_value=50, max_digits=4, decimal_places=2)

    def to_representation(self, instance):
        return {'id': instance.order_id}

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours']


class AssignSerializer(serializers.ModelSerializer):
    orders = serializers.SerializerMethodField()

    @staticmethod
    def get_orders(obj):
        return [{'id': order.order_id} for order in obj.orders.all() if order.complete_time is None]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret['assign_time'] is None:
            del ret['assign_time']
        return ret

    def save(self, courier, *args, **kwargs):
        self.instance = courier

        # don't take new orders once assigned
        if self.instance.assign_time:
            return self.instance

        orders = Order.objects.filter(
            courier__isnull=True, complete_time__isnull=True, region__in=self.instance.regions
        ).order_by('weight')

        # take orders
        total_weight = 0
        capacity = self.instance.capacity
        for order in orders:
            if not has_intersection(order.delivery_hours, courier.working_hours):
                continue
            if total_weight + order.weight <= capacity:
                order.courier = self.instance
                order.save()
                total_weight += order.weight
            else:
                break
        if total_weight == 0:
            return self.instance

        self.instance.assign_time = timezone.now()
        self.instance.save()
        return self.instance

    class Meta:
        model = Courier
        fields = ['assign_time', 'orders']
        read_only_fields = ['assign_time', 'orders']


class CompleteSerializer(serializers.ModelSerializer):
    courier_id = serializers.IntegerField()

    def validate_courier_id(self, value):
        if self.instance.courier is None or self.instance.courier.courier_id != value:
            raise serializers.ValidationError("Order is not assigned to this courier")
        return value

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        del ret['courier_id']
        del ret['complete_time']
        return ret

    def update(self, instance, validated_data):
        if instance.complete_time:
            return instance
        return super().update(instance, validated_data)

    class Meta:
        model = Order
        fields = ['order_id', 'courier_id', 'complete_time']

import re
from collections import OrderedDict, Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail, SkipField, set_value
from rest_framework.settings import api_settings
from rest_framework.validators import UniqueValidator

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


class TimeRangeField(serializers.CharField):
    def to_internal_value(self, data):
        super().to_internal_value(data)
        if not re.fullmatch(r'[0-9]{2}:[0-9]{2}-[0-9]{2}:[0-9]{2}', data):
            raise ValidationError('Incorrect format. Expected `18:55`.')
        time1, time2 = [map(int, time.split(':')) for time in data.split('-')]
        if any([hh > 23 or hh < 0 or mm < 0 or mm > 59 for hh, mm in [time1, time2]]):
            raise ValidationError('Incorrect value. Hours must be between 0 and 23, minutes between 0 and 59.')
        return data


class DeserializerMixin:
    """
    Disallows extra fields and adds an id value to every item with validation errors
    """
    id_field = None

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.
        """
        if not isinstance(data, Mapping):
            message = self.error_messages['invalid'].format(
                datatype=type(data).__name__
            )
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='invalid')

        ret = OrderedDict()
        errors = OrderedDict()
        fields = self._writable_fields

        for field in fields:
            validate_method = getattr(self, 'validate_' + field.field_name, None)
            primitive_value = field.get_value(data)
            try:
                validated_value = field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except ValidationError as exc:
                errors[field.field_name] = exc.detail
            except DjangoValidationError as exc:
                errors[field.field_name] = get_error_detail(exc)
            except SkipField:
                pass
            else:
                set_value(ret, field.source_attrs, validated_value)

        unknown_keys = set(data.keys()) - set(self.fields.keys())
        for key in unknown_keys:
            errors[key] = 'Unexpected field.'

        if errors:
            if self.id_field:
                errors.update({'id': data.get(self.id_field, 0)})
                errors.move_to_end('id', last=False)
            raise ValidationError(errors)

        return ret


class CourierSerializer(DeserializerMixin, serializers.ModelSerializer):
    regions = serializers.ListField(child=serializers.IntegerField(min_value=1))
    working_hours = serializers.ListField(child=TimeRangeField())

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['courier_id'] = instance.courier_id
        ret.move_to_end('courier_id', last=False)
        return ret

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
        fields = ['courier_type', 'regions', 'working_hours']


class CourierShortSerializer(DeserializerMixin, serializers.ModelSerializer):
    id_field = 'courier_id'

    courier_id = serializers.IntegerField(
        min_value=1,
        validators=[UniqueValidator(queryset=Courier.objects.all(), message='Courier with this id already exists.')]
    )
    regions = serializers.ListField(child=serializers.IntegerField(min_value=1))
    working_hours = serializers.ListField(child=TimeRangeField())

    def to_representation(self, instance):
        return {'id': instance.courier_id}

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions', 'working_hours']


class OrderSerializer(DeserializerMixin, serializers.ModelSerializer):
    id_field = 'order_id'

    order_id = serializers.IntegerField(
        min_value=1,
        validators=[UniqueValidator(queryset=Order.objects.all(), message='Order with this id already exists.')]
    )
    weight = serializers.DecimalField(min_value=0.005, max_value=50, max_digits=4, decimal_places=2)
    delivery_hours = serializers.ListField(child=TimeRangeField())

    def to_representation(self, instance):
        return {'id': instance.order_id}

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours']


class AssignSerializer(DeserializerMixin, serializers.ModelSerializer):
    courier_id = serializers.IntegerField(min_value=1, write_only=True)

    @staticmethod
    def get_orders(obj):
        return [{'id': order.order_id} for order in obj.orders.all() if order.complete_time is None]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['orders'] = self.get_orders(instance)
        if instance.assign_time is not None:
            ret['assign_time'] = instance.assign_time.isoformat()
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
        fields = ['courier_id']


class CompleteSerializer(DeserializerMixin, serializers.ModelSerializer):
    courier_id = serializers.IntegerField(min_value=1, write_only=True)
    complete_time = serializers.DateTimeField(write_only=True)

    def validate_courier_id(self, value):
        if self.instance.courier is None or self.instance.courier.courier_id != value:
            raise serializers.ValidationError("Order is not assigned to this courier")
        return value

    def update(self, instance, validated_data):
        if instance.complete_time:
            return instance
        return super().update(instance, validated_data)

    class Meta:
        model = Order
        fields = ['order_id', 'courier_id', 'complete_time']

from rest_framework import status, mixins
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from delivery.models import Courier, Order
from delivery.serializers import CourierSerializer, CourierShortSerializer, OrderSerializer, AssignSerializer, \
    CompleteSerializer
from rest_framework import generics


class CourierCreateView(generics.CreateAPIView):
    """
    API endpoint to create couriers
    """
    queryset = Courier.objects.order_by('courier_id')
    serializer_class = CourierShortSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data['data'], many=True)
        if not serializer.is_valid():
            errors = [
                {**error, 'id': int(error['id']) if error['id'].isdigit() else error['id']}
                for error in serializer.errors
                if error
            ]
            return Response({'validation_error': {'couriers': errors}}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response({'couriers': serializer.data}, status=status.HTTP_201_CREATED)


class CourierUpdateView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to update some parameters of a courier
    """
    queryset = Courier.objects.order_by('courier_id')
    serializer_class = CourierSerializer
    lookup_field = 'courier_id'


class OrderCreateView(generics.CreateAPIView):
    """
    API endpoint to create orders
    """
    queryset = Order.objects.order_by('order_id')
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data['data'], many=True)
        if not serializer.is_valid():
            errors = [
                {**error, 'id': int(error['id']) if error['id'].isdigit() else error['id']}
                for error in serializer.errors
                if error
            ]
            return Response({'validation_error': {'orders': errors}}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response({'orders': serializer.data}, status=status.HTTP_201_CREATED)


class AssignView(generics.GenericAPIView):
    """
    API endpoint to assign the best matching set of orders to a courier
    """
    serializer_class = AssignSerializer
    queryset = Courier.objects.order_by('courier_id')

    def get_object(self):
        courier_id = self.request.data.get('courier_id')
        if not courier_id:
            raise ValidationError('"courier_id": this field is required')
        if not isinstance(courier_id, int) or courier_id < 1:
            raise ValidationError('"courier_id": must be a positive integer')
        obj = self.get_queryset().filter(courier_id=courier_id).first()
        if not obj:
            raise ValidationError(f"Courier #{courier_id} does not exist.")
        return obj

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(courier=self.get_object())
        return Response(serializer.data, status=HTTP_200_OK)


class CompleteView(mixins.UpdateModelMixin, generics.GenericAPIView):
    """
    API endpoint to mark an order as completed
    """
    serializer_class = CompleteSerializer
    queryset = Order.objects.order_by('order_id')

    def get_object(self):
        order_id = self.request.data.get('order_id')
        if not order_id:
            raise ValidationError('"order_id": this field is required')
        if not isinstance(order_id, int) or order_id < 1:
            raise ValidationError('"order_id": must be a positive integer')
        obj = self.get_queryset().filter(order_id=order_id).first()
        if not obj:
            raise ValidationError(f"Order #{order_id} does not exist.")
        return obj

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

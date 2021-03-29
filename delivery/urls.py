from django.urls import path, include

from delivery.views import CourierCreateView, CourierUpdateView, OrderCreateView, AssignView, CompleteView

urlpatterns = [
    path('couriers', CourierCreateView.as_view(), name='couriers'),
    path('couriers/<int:courier_id>', CourierUpdateView.as_view(), name='courier'),
    path('orders', OrderCreateView.as_view(), name='orders'),
    path('orders/assign', AssignView.as_view(), name='assign'),
    path('orders/complete', CompleteView.as_view(), name='complete'),
]

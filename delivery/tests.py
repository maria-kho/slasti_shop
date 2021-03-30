from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from freezegun import freeze_time

from delivery.consts import CAR, FOOT, BIKE
from delivery.models import Courier, Order


class TestCourierCreateView(APITestCase):
    def setUp(self):
        self.path = reverse('couriers')

    def test_basic(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "foot",
                    "regions": [1, 12, 22],
                    "working_hours": ["11:35-14:05", "09:00-11:00"]
                },
                {
                    "courier_id": 3,
                    "courier_type": "bike",
                    "regions": [22],
                    "working_hours": ["09:00-18:00"]
                },
                {
                    "courier_id": 5,
                    "courier_type": "car",
                    "regions": [12, 22, 23, 33],
                    "working_hours": []
                }
            ]
        }
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.data, {"couriers": [{"id": 1}, {"id": 3}, {"id": 5}]})

        # check db
        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 3)
        courier = Courier.objects.get(pk=5)
        self.assertEqual(courier.courier_type, CAR)
        self.assertListEqual(courier.regions, [12, 22, 23, 33])
        self.assertListEqual(courier.working_hours, [])

    def test_extra_field(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "foot",
                    "regions": [1, 12, 22],
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "bad_field": 1000
                },
                {
                    "courier_id": 3,
                    "courier_type": "bike",
                    "regions": [22],
                    "working_hours": ["09:00-18:00"],
                    "meow": "MEOW"
                },
            ]
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_missing_field(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                },
                {
                    "courier_id": 3,
                    "courier_type": "bike",
                    "regions": [22],
                    "working_hours": ["09:00-18:00"]
                },
            ]
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_courier_type(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "ship",
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "regions": [1, 12, 22],
                },
                {
                    "courier_id": 3,
                    "courier_type": "bike",
                    "regions": [22],
                    "working_hours": ["09:00-18:00"]
                },
            ]
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)


class TestCourierUpdateView(APITestCase):
    def setUp(self):
        self.courier_id = 2
        self.path = reverse('courier', args=(self.courier_id,))
        Courier.objects.create(
            courier_id=self.courier_id, courier_type="bike", regions=[15], working_hours=["09:00-18:00"]
        )

    def test_basic(self):
        payload = {"regions": [11, 33, 2], "courier_type": "foot"}
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": "foot",
            "regions": [11, 33, 2],
            "working_hours": ["09:00-18:00"]
        }
        response = self.client.patch(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        # check db
        courier = Courier.objects.get(pk=self.courier_id)
        self.assertEqual(courier.courier_type, FOOT)
        self.assertListEqual(courier.regions, [11, 33, 2])
        self.assertListEqual(courier.working_hours, ["09:00-18:00"])


class TestOrderCreateView(APITestCase):
    def setUp(self):
        self.path = reverse('orders')

    def test_basic(self):
        payload = {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0.23,
                    "region": 12,
                    "delivery_hours": ["09:00-18:00"]
                },
                {
                    "order_id": 2,
                    "weight": 50,
                    "region": 1,
                    "delivery_hours": ["09:00-18:00"]
                },
                {
                    "order_id": 3,
                    "weight": 0.01,
                    "region": 22,
                    "delivery_hours": ["09:00-12:00", "16:00-21:30"]
                }
            ]
        }
        expected_response = {
            "orders": [{"id": 1}, {"id": 2}, {"id": 3}]
        }
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.data, expected_response)

        # check db
        qs = Order.objects.all()
        self.assertEqual(qs.count(), 3)
        order = Order.objects.get(pk=2)
        self.assertEqual(order.weight, 50)
        self.assertEqual(order.region, 1)
        self.assertListEqual(order.delivery_hours, ["09:00-18:00"])


class TestAssignView(APITestCase):
    def setUp(self):
        self.courier_id = 2
        self.path = reverse('assign')
        Courier.objects.create(
            courier_id=self.courier_id, courier_type="bike", regions=[15, 12], working_hours=["09:00-18:00"]
        )
        Order.objects.create(order_id=1, weight=0.23, region=12, delivery_hours=["16:00-18:00"])
        Order.objects.create(order_id=2, weight=14, region=15, delivery_hours=["08:00-09:01"])

    @freeze_time('2021-01-01 13:00:00')
    def test_basic(self):
        payload = {
            "courier_id": self.courier_id
        }
        expected_response = {
            "orders": [{"id": 1}, {"id": 2}],
            "assign_time": "2021-01-01T13:00:00Z"
        }
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        # check db
        qs = Order.objects.filter(courier_id=self.courier_id)
        self.assertEqual(qs.count(), 2)


class TestCompleteView(APITestCase):
    def setUp(self):
        self.order_id = 33
        self.courier_id = 2
        self.path = reverse('complete')
        Courier.objects.create(
            courier_id=self.courier_id, courier_type="bike", regions=[15, 12], working_hours=["09:00-18:00"]
        )
        Order.objects.create(
            order_id=self.order_id, weight=0.23, region=12, delivery_hours=["16:00-18:00"], courier_id=self.courier_id
        )

    def test_basic(self):
        payload = {
            "courier_id": self.courier_id,
            "order_id": self.order_id,
            "complete_time": "2021-01-10T10:33:01.42Z"
        }
        expected_response = {
            "order_id": self.order_id
        }
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        # check db
        order = Order.objects.get(pk=self.order_id)
        self.assertEqual(order.complete_time.isoformat(), "2021-01-10T10:33:01.420000+00:00")

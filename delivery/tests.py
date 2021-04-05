from datetime import datetime

from django.utils import timezone
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from freezegun import freeze_time

from delivery.consts import CAR, FOOT, BIKE
from delivery.models import Courier, Order, Batch


class TestCourierCreateView(APITestCase):
    def setUp(self):
        self.path = reverse('couriers')
        self.maxDiff = None

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
                    "regions": [],
                    "working_hours": ["00:00-23:59"]
                },
                {
                    "courier_id": 5,
                    "courier_type": "car",
                    "regions": [12, 22, 23, 33],
                    "working_hours": []
                }
            ]
        }
        expected_response = {"couriers": [{"id": 1}, {"id": 3}, {"id": 5}]}
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.data, expected_response)

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
                },
                {
                    "courier_id": 3,
                    "courier_type": "bike",
                    "regions": [22],
                    "working_hours": ["09:00-18:00"],
                    "bad_field": 1000
                },
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 3,
                    "bad_field": "Unexpected field."
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

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
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "courier_type": ["This field is required."],
                    "regions": ["This field is required."]
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

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
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "courier_type": ['"ship" is not a valid choice.'],
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_courier_id(self):
        payload = {
            "data": [
                {
                    "courier_id": 0,
                    "courier_type": "bike",
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "regions": [1, 12, 22],
                },
                {
                    "courier_id": 1.5,
                    "courier_type": "bike",
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "regions": [1, 12, 22],
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [
                    {
                        "id": 0,
                        "courier_id": ["Ensure this value is greater than or equal to 1."],
                    },
                    {
                        "id": "1.5",
                        "courier_id": ["A valid integer is required."],
                    },
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_existing_courier(self):
        Courier.objects.create(courier_id=10, courier_type="foot", regions=[], working_hours=[])

        payload = {
            "data": [
                {
                    "courier_id": 10,
                    "courier_type": "bike",
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "regions": [1, 12, 22],
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 10,
                    "courier_id": ["Courier with this id already exists."],
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 1)
        courier = Courier.objects.get(pk=10)
        self.assertEqual(courier.courier_type, FOOT)
        self.assertListEqual(courier.regions, [])
        self.assertListEqual(courier.working_hours, [])

    def test_bad_regions_value(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "bike",
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "regions": [15, "Uralmash", 0],
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "regions": {
                        1: ["A valid integer is required."],
                        2: ["Ensure this value is greater than or equal to 1."]
                    }
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_regions_type(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "bike",
                    "working_hours": ["11:35-14:05", "09:00-11:00"],
                    "regions": 12,
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "regions": ['Expected a list of items but got type "int".']
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_working_hours_format(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "bike",
                    "working_hours": ["11:35-14:05:", "09:00-11:000"],
                    "regions": [12],
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "working_hours": {
                        0: ["Incorrect format. Expected `HH:MM-HH:MM`."],
                        1: ["Incorrect format. Expected `HH:MM-HH:MM`."],
                    }
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_working_hours_value(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "bike",
                    "working_hours": ["11:59-24:05", "05:60-11:00", 10],
                    "regions": [12],
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "working_hours": {
                        0: ["Incorrect value. Hours must be between 0 and 23, minutes between 0 and 59."],
                        1: ["Incorrect value. Hours must be between 0 and 23, minutes between 0 and 59."],
                        2: ['Incorrect type. Expected a string, but got type "int".']
                    }
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_working_hours_type(self):
        payload = {
            "data": [
                {
                    "courier_id": 1,
                    "courier_type": "bike",
                    "working_hours": "11:35-14:05",
                    "regions": [12],
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "couriers": [{
                    "id": 1,
                    "working_hours": ['Expected a list of items but got type "str".']
                }]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Courier.objects.all()
        self.assertEqual(qs.count(), 0)


class TestCourierUpdateView(APITestCase):
    def setUp(self):
        self.courier_id = 2
        self.path = reverse('courier', args=(self.courier_id,))
        Courier.objects.create(
            courier_id=self.courier_id, courier_type=BIKE, regions=[15, 16, 17], working_hours=["09:00-18:00"]
        )
        self.batch = Batch.objects.create(
            current_courier_id=self.courier_id, assign_time=datetime(2021, 3, 29, 9, 30), assign_type=BIKE
        )
        Order.objects.create(order_id=1, weight=3.1, region=15, delivery_hours=["10:00-13:00"], batch=self.batch)
        Order.objects.create(order_id=2, weight=3, region=16, delivery_hours=["10:00-16:00"], batch=self.batch)
        Order.objects.create(order_id=3, weight=2.9, region=17, delivery_hours=["10:00-12:01"], batch=self.batch)
        Order.objects.create(order_id=4, weight=1.01, region=17, delivery_hours=["10:00-12:00"], batch=self.batch)

    def test_basic(self):
        payload = {
            "regions": [20, 17, 16, 15],
            "courier_type": "car",
            "working_hours": ["09:30-17:30"]
        }
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": CAR,
            "regions": [20, 17, 16, 15],
            "working_hours": ["09:30-17:30"]
        }
        response = self.client.patch(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        # check db
        courier = Courier.objects.get(pk=self.courier_id)
        self.assertEqual(courier.courier_type, CAR)
        self.assertListEqual(courier.regions, [20, 17, 16, 15])
        self.assertListEqual(courier.working_hours, ["09:30-17:30"])

        orders = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(orders.count(), 4)

    def test_drop_by_weight(self):
        orders = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(orders.count(), 4)

        payload = {
            "courier_type": "foot",
        }
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": FOOT,
            "regions": [15, 16, 17],
            "working_hours": ["09:00-18:00"]
        }

        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        self.assertEqual(orders.count(), 3)

    def test_drop_by_regions(self):
        orders = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(orders.count(), 4)

        payload = {
            "regions": [15, 17],
        }
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": BIKE,
            "regions": [15, 17],
            "working_hours": ["09:00-18:00"]
        }

        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        self.assertEqual(orders.count(), 3)

    def test_drop_by_hours(self):
        orders = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(orders.count(), 4)

        payload = {
            "working_hours": ["12:00-18:00"],
        }
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": BIKE,
            "regions": [15, 16, 17],
            "working_hours": ["12:00-18:00"]
        }

        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        self.assertEqual(orders.count(), 3)

    def test_drop_multiple(self):
        orders = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(orders.count(), 4)

        payload = {
            "courier_type": "foot",
            "working_hours": ["12:00-18:00"],
            "regions": [15, 16]
        }
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": FOOT,
            "regions": [15, 16],
            "working_hours": ["12:00-18:00"]
        }

        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        self.assertEqual(orders.count(), 2)

    def test_drop_multiple_heavy(self):
        Order.objects.filter(order_id=1).update(weight=8)
        orders = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(orders.count(), 4)

        payload = {
            "courier_type": "foot",
            "working_hours": ["12:00-18:00"],
            "regions": [15, 16]
        }
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": FOOT,
            "regions": [15, 16],
            "working_hours": ["12:00-18:00"]
        }

        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().pk, 2)

    def test_missing_fields(self):
        payload = {"regions": [11, 33, 2]}
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": BIKE,
            "regions": [11, 33, 2],
            "working_hours": ["09:00-18:00"]
        }
        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        courier = Courier.objects.get(pk=self.courier_id)
        self.assertEqual(courier.courier_type, BIKE)
        self.assertListEqual(courier.regions, [11, 33, 2])
        self.assertListEqual(courier.working_hours, ["09:00-18:00"])

    def test_extra_field(self):
        payload = {
            "regions": [11, 33, 2],
            "courier_type": "foot",
            "courier_id": 5
        }
        expected_response = {
            "courier_id": "Unexpected field."
        }
        response = self.client.patch(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

    def test_not_found(self):
        path = reverse('courier', args=(5,))
        payload = {
            "regions": [11, 33, 2],
            "courier_type": "foot",
        }
        expected_response = {
            "detail": "Not found."
        }
        response = self.client.patch(path, payload, format='json')
        self.assertEqual(response.status_code, 404)
        self.assertDictEqual(response.data, expected_response)


class TestOrderCreateView(APITestCase):
    def setUp(self):
        self.path = reverse('orders')
        self.maxDiff = None

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

    def test_missing_fields(self):
        payload = {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0.23,
                    "delivery_hours": ["09:00-18:00"]
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "orders": [
                    {
                        "id": 1,
                        "region": ["This field is required."]
                    },
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Order.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_extra_fields(self):
        payload = {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0.23,
                    "region": 1,
                    "courier_id": 5,
                    "delivery_hours": ["09:00-18:00"]
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "orders": [
                    {
                        "id": 1,
                        "courier_id": "Unexpected field."
                    },
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Order.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_region(self):
        payload = {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0.23,
                    "region": 0,
                    "delivery_hours": ["09:00-18:00"]
                },
                {
                    "order_id": 2,
                    "weight": 50,
                    "region": "Uralmash",
                    "delivery_hours": ["09:00-18:00"]
                },
            ]
        }
        expected_response = {
            "validation_error": {
                "orders": [
                    {
                        "id": 1,
                        "region": ["Ensure this value is greater than or equal to 1."],
                    },
                    {
                        "id": 2,
                        "region": ["A valid integer is required."]
                    },
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Order.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_bad_weight(self):
        payload = {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0,
                    "region": 1,
                    "delivery_hours": ["09:00-18:00"]
                },
                {
                    "order_id": 2,
                    "weight": 50.01,
                    "region": 2,
                    "delivery_hours": ["09:00-18:00"]
                },
                {
                    "order_id": 3,
                    "weight": 5.005,
                    "region": 2,
                    "delivery_hours": ["09:00-18:00"]
                },
            ]
        }
        expected_response = {
            "validation_error": {
                "orders": [
                    {
                        "id": 1,
                        "weight": ["Ensure this value is greater than or equal to 0.005."],
                    },
                    {
                        "id": 2,
                        "weight": ["Ensure this value is less than or equal to 50."]
                    },
                    {
                        "id": 3,
                        "weight": ["Ensure that there are no more than 2 decimal places."]
                    },
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Order.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_existing_order(self):
        Order.objects.create(order_id=10, weight=25, region=5, delivery_hours=["10:00-12:00"])
        payload = {
            "data": [
                {
                    "order_id": 10,
                    "weight": 0.23,
                    "region": 5,
                    "delivery_hours": ["09:00-18:00"]
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "orders": [
                    {
                        "id": 10,
                        "order_id": ["Order with this id already exists."],
                    }
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Order.objects.all()
        self.assertEqual(qs.count(), 1)

    def test_bad_order_id(self):
        payload = {
            "data": [
                {
                    "order_id": 0,
                    "weight": 0.23,
                    "region": 5,
                    "delivery_hours": ["09:00-18:00"]
                },
                {
                    "order_id": 1.5,
                    "weight": 0.23,
                    "region": 5,
                    "delivery_hours": ["09:00-18:00"]
                }
            ]
        }
        expected_response = {
            "validation_error": {
                "orders": [
                    {
                        "id": 0,
                        "order_id": ["Ensure this value is greater than or equal to 1."],
                    },
                    {
                        "id": "1.5",
                        "order_id": ["A valid integer is required."],
                    }
                ]
            }
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.data, expected_response)

        qs = Order.objects.all()
        self.assertEqual(qs.count(), 0)


class TestAssignView(APITestCase):
    def setUp(self):
        self.courier_id = 2
        self.path = reverse('assign')
        Courier.objects.create(
            courier_id=self.courier_id, courier_type=BIKE, regions=[15, 12], working_hours=["09:00-18:00"]
        )

    @freeze_time('2021-01-01 13:00:00')
    def test_basic(self):
        Order.objects.create(order_id=1, weight=0.19, region=12, delivery_hours=["16:00-18:00"])
        Order.objects.create(order_id=2, weight=14.81, region=15, delivery_hours=["08:00-09:01"])

        payload = {
            "courier_id": self.courier_id
        }
        expected_response = {
            "orders": [{"id": 1}, {"id": 2}],
            "assign_time": "2021-01-01T13:00:00+00:00"
        }
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        # check db
        qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(qs.count(), 2)
        batch = Batch.objects.get(current_courier_id=self.courier_id)
        self.assertEqual(batch.assign_time.isoformat(), "2021-01-01T13:00:00+00:00")
        self.assertEqual(batch.assign_type, BIKE)

    @freeze_time('2021-01-01 13:00:00')
    def test_assign_by_weight(self):
        for i in range(1, 5):
            Order.objects.create(order_id=i, weight=4, region=15, delivery_hours=["09:00-18:00"])

        payload = {
            "courier_id": self.courier_id
        }
        expected_response = {
            "orders": [{"id": 1}, {"id": 2}, {"id": 3}],
            "assign_time": "2021-01-01T13:00:00+00:00"
        }
        response = self.client.post(self.path, payload, format='json')

        # check response
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        # check db
        qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(qs.count(), 3)

    @freeze_time('2021-01-01 13:00:00')
    def test_assign_by_regions_and_hours(self):
        Order.objects.create(order_id=1, weight=2, region=15, delivery_hours=["09:00-18:00"])
        Order.objects.create(order_id=2, weight=2, region=9, delivery_hours=["09:00-18:00"])
        Order.objects.create(order_id=3, weight=2, region=12, delivery_hours=["09:00-18:00"])

        payload = {
            "courier_id": self.courier_id
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)

        qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(qs.count(), 2)

    @freeze_time('2021-01-01 13:00:00')
    def test_all(self):
        Order.objects.create(order_id=1, weight=4, region=15, delivery_hours=["08:00-20:00"])
        Order.objects.create(order_id=2, weight=4, region=9, delivery_hours=["09:00-18:00"])
        Order.objects.create(order_id=3, weight=4, region=12, delivery_hours=["09:00-18:00"])
        Order.objects.create(order_id=4, weight=4, region=15, delivery_hours=["19:00-20:00"])
        Order.objects.create(order_id=5, weight=4, region=12, delivery_hours=["13:00-16:00"])
        Order.objects.create(order_id=6, weight=4, region=12, delivery_hours=["09:00-18:00"])

        payload = {
            "courier_id": self.courier_id
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)

        qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(qs.count(), 3)

    @freeze_time('2021-01-01 13:00:00')
    def test_nothing(self):
        Order.objects.create(order_id=1, weight=16, region=12, delivery_hours=["09:00-18:00"])
        Order.objects.create(order_id=2, weight=4, region=9, delivery_hours=["09:00-20:00"])
        Order.objects.create(order_id=3, weight=4, region=12, delivery_hours=["20:00-21:00"])

        payload = {
            "courier_id": self.courier_id
        }
        expected_response = {
            "orders": [],
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertDictEqual(response.data, expected_response)
        self.assertEqual(response.status_code, 200)

        qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
        self.assertEqual(qs.count(), 0)
        courier = Courier.objects.get(pk=self.courier_id)
        self.assertFalse(hasattr(courier, 'current_batch'))

    def test_complete(self):
        for i in range(1, 6):
            Order.objects.create(order_id=i, weight=3, region=15, delivery_hours=["09:00-18:00"])

        payload = {
            "courier_id": self.courier_id
        }
        expected_response = {
            "orders": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}],
            "assign_time": "2021-01-01T13:00:00+00:00"
        }
        with freeze_time('2021-01-01 13:00:00') as ft:
            response = self.client.post(self.path, payload, format='json')
            self.assertDictEqual(response.data, expected_response)
            self.assertEqual(response.status_code, 200)

            qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
            self.assertEqual(qs.count(), 5)

            ft.tick()

            Order.objects.filter(pk__in=[2, 4]).update(complete_time=timezone.now())
            response = self.client.post(self.path, payload, format='json')
            expected_response = {
                "orders": [{"id": 1}, {"id": 3}, {"id": 5}],
                "assign_time": "2021-01-01T13:00:00+00:00"
            }
            self.assertDictEqual(response.data, expected_response)
            self.assertEqual(response.status_code, 200)

            qs = Order.objects.filter(batch__current_courier_id=self.courier_id)
            self.assertEqual(qs.count(), 5)


class TestCompleteView(APITestCase):
    def setUp(self):
        self.order_id = 33
        self.courier_id = 2
        self.path = reverse('complete')
        Courier.objects.create(
            courier_id=self.courier_id, courier_type=BIKE, regions=[15, 12], working_hours=["09:00-18:00"],
        )
        self.batch = Batch.objects.create(
            current_courier_id=self.courier_id, assign_time=datetime(2021, 1, 10, 9, 0), assign_type=BIKE
        )
        Order.objects.create(
            order_id=self.order_id, weight=0.23, region=12, delivery_hours=["16:00-18:00"], batch=self.batch
        )

    def test_not_last_order(self):
        Order.objects.create(
            order_id=self.order_id + 1, weight=0.23, region=12, delivery_hours=["16:00-18:00"],
            batch=self.batch
        )
        payload = {
            "courier_id": self.courier_id,
            "order_id": self.order_id,
            "complete_time": "2021-01-10T10:33:01.42Z"
        }
        expected_response = {
            "order_id": self.order_id
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        order = Order.objects.get(pk=self.order_id)
        self.assertEqual(order.complete_time.isoformat(), "2021-01-10T10:33:01.420000+00:00")
        courier = Courier.objects.get(pk=self.courier_id)
        self.assertEqual(courier.current_batch, self.batch)

        # does not change the complete time if the order is already completed
        payload = {
            "courier_id": self.courier_id,
            "order_id": self.order_id,
            "complete_time": "2021-03-15T12:30:00Z"
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        order.refresh_from_db()
        self.assertEqual(order.complete_time.isoformat(), "2021-01-10T10:33:01.420000+00:00")
        courier.refresh_from_db()
        self.assertEqual(courier.current_batch, self.batch)
        self.assertIsNone(courier.past_batches.last())

    def test_last_order(self):
        courier = Courier.objects.get(pk=self.courier_id)
        self.assertIsNone(courier.past_batches.last())
        self.assertEqual(courier.current_batch, self.batch)

        payload = {
            "courier_id": self.courier_id,
            "order_id": self.order_id,
            "complete_time": "2021-01-10T10:33:01.42Z"
        }
        expected_response = {
            "order_id": self.order_id
        }
        response = self.client.post(self.path, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

        order = Order.objects.get(pk=self.order_id)
        self.assertEqual(order.complete_time.isoformat(), "2021-01-10T10:33:01.420000+00:00")
        courier.refresh_from_db()
        self.assertFalse(hasattr(courier, 'current_batch'))
        self.assertEqual(courier.past_batches.last(), self.batch)


class TestCourierRetrieveView(APITestCase):
    def setUp(self):
        self.courier_id = 2
        self.path = reverse('courier', args=(self.courier_id,))
        Courier.objects.create(
            courier_id=self.courier_id, courier_type=BIKE, regions=[15, 16, 17], working_hours=["09:00-18:00"],
        )
        self.batch = Batch.objects.create(
            past_courier_id=self.courier_id, assign_type=BIKE, assign_time=datetime(2021, 3, 29, 9, 30)
        )
        Order.objects.create(order_id=3, weight=3.1, region=15, delivery_hours=["09:00-18:00"], batch=self.batch,
                             complete_time=datetime(2021, 3, 29, 10, 0))
        Order.objects.create(order_id=2, weight=3, region=15, delivery_hours=["09:00-18:00"], batch=self.batch,
                             complete_time = datetime(2021, 3, 29, 10, 30))
        Order.objects.create(order_id=5, weight=3, region=15, delivery_hours=["09:00-18:00"], batch=self.batch,
                             complete_time = datetime(2021, 3, 29, 11, 30))
        Order.objects.create(order_id=1, weight=2.9, region=17, delivery_hours=["09:00-18:00"], batch=self.batch,
                             complete_time = datetime(2021, 3, 29, 12, 30))
        self.batch2 = Batch.objects.create(
            past_courier_id=self.courier_id, assign_type=FOOT, assign_time=datetime(2021, 3, 29, 12, 30)
        )
        Order.objects.create(order_id=4, weight=1.01, region=17, delivery_hours=["09:00-18:00"], batch=self.batch2,
                             complete_time = datetime(2021, 3, 29, 13, 00))

    def test_basic(self):
        expected_response = {
            "courier_id": self.courier_id,
            "courier_type": BIKE,
            "regions": [15, 16, 17],
            "working_hours": ["09:00-18:00"],
            "rating": 1.67,
            "earnings": 500 * 2 + 500 * 5
        }
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

    def test_null_rating(self):
        Courier.objects.create(
            courier_id=5, courier_type=BIKE, regions=[15, 16, 17], working_hours=["09:00-18:00"],
        )
        Batch.objects.create(current_courier_id=5, assign_type=FOOT, assign_time=datetime(2021, 3, 29, 9, 30))
        Order.objects.create(order_id=6, weight=1.01, region=17, delivery_hours=["09:00-18:00"], batch=self.batch,
                             complete_time = datetime(2021, 3, 29, 13, 00))
        expected_response = {
            "courier_id": 5,
            "courier_type": BIKE,
            "regions": [15, 16, 17],
            "working_hours": ["09:00-18:00"],
            "earnings": 0
        }
        path = reverse('courier', args=(5,))

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, expected_response)

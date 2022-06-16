import logging

from django.test import LiveServerTestCase

from registry.models import Component
from registry.serializers import ComponentSerializer

logger = logging.getLogger(__name__)


class ModelTests(LiveServerTestCase):
    def setUp(self):
        pass

    def test_serializers(self):
        self.assertEqual(Component.objects.count(), 0)
        # Create two Components
        c_id = "aabbcc"
        component = Component.objects.create(
            identifier=c_id, body={"foo": "bar", "baz": "bat"}
        )
        component = Component.objects.get(identifier=c_id)
        c_two_id = "ddeeff"
        component_two = Component.objects.create(
            identifier=c_two_id, body={"fooz": "barz", "bazz": "batz"}
        )
        component_two = Component.objects.get(identifier=c_two_id)
        # Check they made it to the DB
        self.assertEqual(Component.objects.count(), 2)
        c_ser = ComponentSerializer(component)
        self.assertEqual(c_ser.data["identifier"], c_id)
        self.assertEqual(c_ser.data["body"]["foo"], "bar")
        self.assertEqual(c_ser.data["body"]["baz"], "bat")
        c_two_ser = ComponentSerializer(component_two)
        self.assertEqual(c_two_ser.data["identifier"], c_two_id)
        self.assertEqual(c_two_ser.data["body"]["fooz"], "barz")
        self.assertEqual(c_two_ser.data["body"]["bazz"], "batz")

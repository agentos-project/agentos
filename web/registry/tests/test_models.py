import logging

from django.test import LiveServerTestCase
from registry.models import Component, ComponentDependency, Repo
from registry.serializers import ComponentSerializer

logger = logging.getLogger(__name__)


class ModelTests(LiveServerTestCase):
    def setUp(self):
        pass

    def test_serializers(self):
        r = Repo.objects.create(identifier="r")
        component = Component.objects.create(
            identifier="x",
            name="x",
            version="1",
            repo=r,
            class_name="X",
            file_path=".",
            instantiate=False,
        )
        component_two = Component.objects.create(
            identifier="y",
            name="y",
            version="1",
            repo=r,
            class_name="X",
            file_path=".",
            instantiate=False,
        )
        cd = ComponentDependency(
            depender=component, dependee=component_two, attribute_name="x"
        )
        self.assertIsNotNone(component_two.dependencies.all())
        cd.save()
        self.assertEqual(component.depender_set.count(), 1)
        self.assertEqual(component.dependee_set.count(), 0)
        self.assertEqual(component.dependencies.count(), 1)
        c_ser = ComponentSerializer(component)
        self.assertEqual(c_ser.data["identifier"], "x")

import unittest

from nifc_wildfires import get_active_perimeters, get_incidents


class NifcUnitTest(unittest.TestCase):
    def test_active_perimeters(self):
        get_active_perimeters()

    def test_incidents(self):
        get_incidents()


if __name__ == "__main__":
    unittest.main()

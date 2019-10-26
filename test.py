#! /usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from geomac_wildfires import (
    get_active_perimeters,
    get_all_perimeters,
    get_nifc_incidents
)


class GeomacWildfiresUnitTest(unittest.TestCase):

    def test_active_perimeters(self):
        get_active_perimeters()

    def test_all_perimeters(self):
        get_all_perimeters()

    def test_nifc_incidents(self):
        get_nifc_incidents()


if __name__ == '__main__':
    unittest.main()

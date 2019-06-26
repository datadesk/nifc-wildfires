#! /usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from geomac_active_fires import get_active_fire_perimeters


class GeoMACActiveFiresUnitTest(unittest.TestCase):

    def test_geomac(self):
        get_active_fire_perimeters()


if __name__ == '__main__':
    unittest.main()

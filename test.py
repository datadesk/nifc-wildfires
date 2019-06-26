#! /usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from geomac_wildfires import get_active_fires


class GeomacWildfiresUnitTest(unittest.TestCase):

    def test_geomac(self):
        get_active_fires()


if __name__ == '__main__':
    unittest.main()

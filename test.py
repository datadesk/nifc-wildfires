#! /usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from geomac_active_fires import get_geomac


class MyUnitTest(unittest.TestCase):

    def test_geomac(self):
        get_geomac()


if __name__ == '__main__':
    unittest.main()

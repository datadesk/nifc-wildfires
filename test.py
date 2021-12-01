#! /usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nifc_wildfires import (
    get_current_perimeters,
    get_nifc_incidents
)


class NifcUnitTest(unittest.TestCase):

    def test_current_perimeters(self):
        get_current_perimeters()

    def test_nifc_incidents(self):
        get_nifc_incidents()


if __name__ == '__main__':
    unittest.main()

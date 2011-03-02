#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import unittest

from test_update import *
from test_commit_basic import *
from test_commit_conflicts import *

if __name__ == '__main__':
    suite = unittest.TestSuite ()

    suite.addTest (unittest.TestLoader ().loadTestsFromTestCase (TestUpdate))

    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestCommitBasic))
    
    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestCommitConflicts))

    unittest.TextTestRunner (verbosity=2).run (suite)

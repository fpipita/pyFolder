#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import unittest

from test_update_basic import *
from test_update_conflicts import *
from test_commit_basic import *
from test_commit_conflicts import *
from test_commit_rights import *

if __name__ == '__main__':
    suite = unittest.TestSuite ()

    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestUpdateBasic))

    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestUpdateConflicts))

    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestCommitBasic))
    
    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestCommitConflicts))

    suite.addTest (\
        unittest.TestLoader ().loadTestsFromTestCase (TestCommitRights))

    unittest.TextTestRunner (verbosity=2).run (suite)

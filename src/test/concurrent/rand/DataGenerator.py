# -*- coding: utf-8 -*-



import random
import sys



sys.path.append ('../')



from common.constants import *



class DataGenerator:



    @staticmethod
    def generate (MinSize, MaxSize):

        Size = random.randint (MinSize, MaxSize)
        RandomData = str ('\0' * Size)

        return RandomData

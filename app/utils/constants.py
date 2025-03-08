# Put this in a common module like app/utils/constants.py
from enum import Enum

class TryOnCategory(Enum):
    TOPS = "tops"
    BOTTOMS = "bottoms"
    DRESSES = "dresses"
    OUTERWEAR = "outerwear"
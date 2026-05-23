
import sys
import os

sys.path.append(os.path.abspath("."))

from csv_validator import detect_csv_issues


def test_corrupted_csv_detection():

    result = detect_csv_issues("corrupted.csv")

    assert len(result["issues"]) > 0

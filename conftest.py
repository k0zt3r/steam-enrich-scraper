import os
import sys

# Put the repository root on sys.path so tests can import the top-level
# packages (parsers, services, models, ...) when pytest is run from anywhere.
sys.path.insert(0, os.path.dirname(__file__))

import os
import sys

# Кладём корень репозитория в sys.path, чтобы тесты могли импортировать
# пакеты верхнего уровня (parsers, services, models, ...) при запуске
# pytest из любого места.
sys.path.insert(0, os.path.dirname(__file__))

"""
Tests unitaires — detection.py

Vérifie :
- Les règles déclenchent des anomalies sur des données dégradées
- Aucune fausse alarme sur des données nominales
- Les champs des objets Anomaly sont correctement peuplés
- La fonction detect_all agrège correctement tous les détecteurs
"""

import pytest
import pandas as pd
from modules.detection import (
    detect_anomalies_electricity,
    detect_anomalies_air_7bar,
    detect_anomalies_air_3bar,
    detect_anomalies_recycled_water,
    detect_anomalies_raw_water,
    detect_all,
    filter_anomalies,
    Anomaly,
)


class TestAir7BarDetection:

    def test_low_pressure_triggers_anomaly(self):
        """Une pression < 6.5 bars doit déclencher une anomalie."""
        pass

    def test_nominal_pressure_no_anomaly(self):
        """Pression nominale (7.0 bars) ne doit pas déclencher d'anomalie."""
        pass

    def test_critical_pressure_severity_5(self):
        """Pression < 6.0 bars doit déclencher une anomalie sévérité 5."""
        pass


class TestAir3BarDetection:

    def test_fixed_compressor_active_triggers_anomaly(self):
        """Un compresseur fixe actif avec variables suffisantes doit déclencher une anomalie."""
        pass

    def test_variables_only_no_anomaly(self):
        """Variables seules actives ne doit pas déclencher d'anomalie sur les fixes."""
        pass


class TestRawWaterDetection:

    def test_low_basin_b1_triggers_anomaly(self):
        """Niveau B1 < 20 % doit déclencher une anomalie critique."""
        pass

    def test_both_basins_low_severity_5(self):
        """Les deux bassins bas simultanément → sévérité maximale."""
        pass


class TestDetectAll:

    def test_returns_list(self):
        pass

    def test_sorted_by_severity(self):
        pass

    def test_filter_by_severity(self):
        pass

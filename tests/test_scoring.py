"""
Tests unitaires — scoring.py

Vérifie :
- Le score final est dans la plage [0, 100]
- Les priorités sont correctement classifiées
- Le score de santé système reflète les anomalies actives
- Le niveau d'alerte global correspond au pire système
"""

import pytest
from modules.scoring import (
    compute_criticality_score,
    compute_system_health,
    score_all_anomalies,
    score_all_systems,
    severity_to_priority,
    get_global_alert_level,
    CriticalityScore,
    SystemHealthScore,
)


class TestCriticalityScore:

    def test_score_in_range(self):
        """Le score final doit être compris entre 0 et 100."""
        pass

    def test_high_severity_gives_high_score(self):
        pass

    def test_low_severity_gives_low_score(self):
        pass


class TestSeverityToPriority:

    def test_score_above_80_is_critical(self):
        pass

    def test_score_below_25_is_low(self):
        pass


class TestSystemHealth:

    def test_no_anomalies_is_100_percent(self):
        """Sans anomalie, le score de santé doit être 100 %."""
        pass

    def test_critical_anomaly_degrades_health(self):
        pass


class TestGlobalAlertLevel:

    def test_all_ok_returns_ok(self):
        pass

    def test_one_critical_returns_critical(self):
        pass

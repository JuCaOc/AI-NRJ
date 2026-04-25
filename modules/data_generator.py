"""
Génération de données mockées réalistes pour l'ensemble des utilities.

Toutes les séries temporelles sont reproductibles via un seed fixe.
Les données originales ne sont jamais modifiées — les transformations
retournent de nouveaux DataFrames.
"""

import numpy as np
import pandas as pd
from typing import Optional

DEFAULT_SEED = 42
DEFAULT_POINTS = 288  # 24h à pas de 5 minutes


# ---------------------------------------------------------------------------
# Électricité
# ---------------------------------------------------------------------------

def generate_electricity_63kv(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du poste source 63 kV.

    Colonnes retournées :
        timestamp, puissance_mw, tension_kv, courant_ka,
        source_reseau_pct, source_cat_pct
    """
    pass


def generate_electricity_15kv(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du réseau 15 kV (force motrice).

    Colonnes retournées :
        timestamp, puissance_mw, tension_kv, charge_pct
    """
    pass


def generate_electricity_55kv(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du réseau 5,5 kV (gros moteurs).

    Colonnes retournées :
        timestamp, puissance_mw, tension_kv,
        compresseurs_kw, pompes_eau_salee_kw, pompes_mpc_kw
    """
    pass


def generate_electricity_400v(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du réseau 400 V (auxiliaires).

    Colonnes retournées :
        timestamp, puissance_kw, tension_v, charge_pct
    """
    pass


# ---------------------------------------------------------------------------
# Air 7 bars (instrumentation)
# ---------------------------------------------------------------------------

COMPRESSORS_7BAR = ["C713", "C714", "C715", "C716", "C717"]


def generate_air_7bar(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du réseau air 7 bars.

    Colonnes retournées :
        timestamp, pression_bar, debit_nm3h,
        C713_etat, C714_etat, C715_etat, C716_etat, C717_etat,
        C713_debit, C714_debit, C715_debit, C716_debit, C717_debit,
        C713_conso_kw, C714_conso_kw, C715_conso_kw, C716_conso_kw, C717_conso_kw
    """
    pass


# ---------------------------------------------------------------------------
# Air 3 bars (transport poussières / charbon)
# ---------------------------------------------------------------------------

COMPRESSORS_3BAR_VARIABLE = ["C321", "C322", "C323"]
COMPRESSORS_3BAR_FIXED = ["C311", "C312"]


def generate_air_3bar(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du réseau air 3 bars.

    Règle : les variables (C321-C323) absorbent la demande ;
    les fixes (C311-C312) n'interviennent qu'en complément.

    Colonnes retournées :
        timestamp, pression_bar, debit_nm3h,
        C321_debit, C322_debit, C323_debit,
        C311_etat, C312_etat,
        demande_nm3h, part_variable_pct
    """
    pass


# ---------------------------------------------------------------------------
# Eau recyclée
# ---------------------------------------------------------------------------

def generate_recycled_water(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du circuit eau recyclée.

    Colonnes retournées :
        timestamp, debit_m3h, temperature_c,
        conductivite_us_cm, ph, turbidite_ntu,
        legionelle_risk_score, tours_actives
    """
    pass


# ---------------------------------------------------------------------------
# Eau brute
# ---------------------------------------------------------------------------

def generate_raw_water(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> pd.DataFrame:
    """
    Génère les données du circuit eau brute.

    Colonnes retournées :
        timestamp,
        B0_niveau_pct, B0_volume_m3,
        B1_niveau_pct, B1_volume_m3,
        debit_appoint_m3h, debit_secours_m3h
    """
    pass


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

def generate_all(
    n_points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    scenario: Optional[str] = None,
) -> dict[str, pd.DataFrame]:
    """
    Génère l'ensemble des flux de données en une seule passe.

    Retourne un dict avec les clés :
        electricity_63kv, electricity_15kv, electricity_55kv, electricity_400v,
        air_7bar, air_3bar, recycled_water, raw_water
    """
    pass

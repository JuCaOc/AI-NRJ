"""
Génération de données mockées industrielles réalistes.

Aucune anomalie intentionnelle — toutes les séries représentent un
fonctionnement nominal reproductible (seed fixe).
Les contraintes physiques (bilans énergie, pressions) sont respectées.
"""

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Configuration globale
# ─────────────────────────────────────────────────────────────────────────────

SEED: int = 42
N_POINTS: int = 96           # 24 h × 15 min
INTERVAL_MIN: int = 15
START_DATE: str = "2024-01-15 00:00:00"

# ─────────────────────────────────────────────────────────────────────────────
# Nominaux physiques — modifiez ici pour calibrer sur une vraie usine
# ─────────────────────────────────────────────────────────────────────────────

_FURNACE_NOM_MW: tuple = (11.0, 9.5, 8.5)     # puissance nominale fours 1-2-3
_CAT_NOM_MW: float = 18.0                       # génération centrale CAT

_C7_NAMES: list = ["C713", "C714", "C715", "C716", "C717"]
_C7_RUN_THRESH: dict = {                         # production_index min pour démarrage
    "C713": 0.00, "C714": 0.00,
    "C715": 0.63, "C716": 0.90, "C717": 0.72,
}
_C7_NOM_FLOW: int = 1_380                        # Nm³/h à pleine charge
_C7_NOM_POWER: int = 142                         # kW à pleine charge

_C3_VAR_MAX_FLOW: int = 880                      # Nm³/h à 100 % VSD
_C3_VAR_MAX_POWER: int = 92                      # kW à 100 % VSD

_RW_NOM_FLOW: int = 820                          # m³/h nominal eau recyclée
_RW_SUPPLY_TEMP: float = 24.0                    # °C départ nominal
_RW_DELTA_T_NOM: float = 6.5                     # °C (retour − départ) nominal

_B0_CAPACITY_M3: int = 1_200                     # volume total bassin B0
_B1_CAPACITY_M3: int = 800                       # volume total bassin B1


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires internes
# ─────────────────────────────────────────────────────────────────────────────

def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _day_factor(
    hours: np.ndarray,
    base: float = 0.60,
    peak: float = 0.97,
) -> np.ndarray:
    """Profil journalier lisse, pic à 13 h, bas la nuit."""
    raw = np.sin(np.pi * (hours - 5.0) / 16.0)
    return base + (peak - base) * np.clip(raw, 0.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 1 — Timeline & production index
# ─────────────────────────────────────────────────────────────────────────────

def generate_base_timeseries(seed: int = SEED) -> pd.DataFrame:
    """
    Crée les 96 horodatages (pas 15 min) et le production_index [0.5 – 1.0].
    Toutes les autres séries se greffent sur ce DataFrame.
    """
    rng = _rng(seed)
    timestamps = pd.date_range(start=START_DATE, periods=N_POINTS, freq=f"{INTERVAL_MIN}min")
    hours = timestamps.hour + timestamps.minute / 60.0

    base = _day_factor(hours.values)
    noise = rng.normal(0.0, 0.014, N_POINTS)
    production_index = np.clip(base + noise, 0.50, 1.00).round(4)

    return pd.DataFrame({
        "timestamp": timestamps,
        "production_index": production_index,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 2 — Électricité
# ─────────────────────────────────────────────────────────────────────────────

def generate_electricity_data(df: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """
    Ajoute les colonnes électriques en respectant la hiérarchie :
    63 kV (fours + CAT + réseau) → 15 kV → 5,5 kV / 400 V.

    Contraintes :
        total_63kv_bus ≈ Σ fours + station_15kv_supply
        station_15kv_supply ≈ Σ sous-stations
        grid_import = total_bus − CAT
    """
    rng = _rng(seed + 100)
    n = len(df)
    prod = df["production_index"].values

    # ── Fours (charges 63 kV directes) ───────────────────────────────────
    for i, nom in enumerate(_FURNACE_NOM_MW, 1):
        col = f"furnace_{i}_63kv_mw"
        noise = rng.normal(0.0, 0.08, n)
        df[col] = np.clip(nom * prod + noise, 0.0, nom * 1.05).round(3)

    # ── CAT (génération interne quasi-constante) ──────────────────────────
    df["cat_generation_63kv_mw"] = np.clip(
        _CAT_NOM_MW + rng.normal(0.0, 0.15, n), 15.0, 21.0
    ).round(3)

    # ── Sous-stations 15 kV ───────────────────────────────────────────────
    # Substation A : gros moteurs 5,5 kV + compresseurs air
    df["substation_a_15kv_mw"] = np.clip(
        12.5 * (0.70 + 0.30 * prod) + rng.normal(0.0, 0.12, n), 7.0, 14.0
    ).round(3)

    # Substation B : pompes eau + moteurs moyens
    df["substation_b_15kv_mw"] = np.clip(
        7.8 * (0.65 + 0.35 * prod) + rng.normal(0.0, 0.09, n), 4.0, 9.5
    ).round(3)

    # Substation C : auxiliaires 400 V
    df["substation_c_15kv_mw"] = np.clip(
        4.4 * (0.70 + 0.30 * prod) + rng.normal(0.0, 0.06, n), 2.8, 5.5
    ).round(3)

    df["station_15kv_supply_mw"] = (
        df["substation_a_15kv_mw"]
        + df["substation_b_15kv_mw"]
        + df["substation_c_15kv_mw"]
        + rng.normal(0.0, 0.05, n)      # pertes réseau légères
    ).clip(lower=0.0).round(3)

    # ── Charges 5,5 kV ───────────────────────────────────────────────────
    df["compressors_7b_5_5kv_mw"] = np.clip(
        0.38 + 0.13 * prod + rng.normal(0.0, 0.012, n), 0.25, 0.60
    ).round(4)

    df["salt_water_pumps_5_5kv_mw"] = np.clip(
        0.60 * (0.70 + 0.30 * prod) + rng.normal(0.0, 0.015, n), 0.40, 0.74
    ).round(4)

    df["mpc_pumps_5_5kv_mw"] = np.clip(
        0.42 * (0.65 + 0.35 * prod) + rng.normal(0.0, 0.010, n), 0.28, 0.52
    ).round(4)

    df["motors_5_5kv_mw"] = np.clip(
        8.5 * (0.55 + 0.45 * prod) + rng.normal(0.0, 0.10, n), 4.5, 10.5
    ).round(3)

    # ── Charges 400 V ────────────────────────────────────────────────────
    df["auxiliaries_400v_mw"] = np.clip(
        1.40 + 0.20 * prod + rng.normal(0.0, 0.040, n), 1.10, 1.90
    ).round(4)

    df["other_motors_400v_mw"] = np.clip(
        2.20 * (0.60 + 0.40 * prod) + rng.normal(0.0, 0.060, n), 1.20, 3.10
    ).round(4)

    # ── Agrégats ─────────────────────────────────────────────────────────
    furnace_sum = (
        df["furnace_1_63kv_mw"] + df["furnace_2_63kv_mw"] + df["furnace_3_63kv_mw"]
    )
    df["total_63kv_bus_mw"] = (furnace_sum + df["station_15kv_supply_mw"]).round(3)

    df["total_plant_power_mw"] = (
        furnace_sum
        + df["compressors_7b_5_5kv_mw"]
        + df["salt_water_pumps_5_5kv_mw"]
        + df["mpc_pumps_5_5kv_mw"]
        + df["motors_5_5kv_mw"]
        + df["auxiliaries_400v_mw"]
        + df["other_motors_400v_mw"]
    ).round(3)

    df["grid_import_63kv_mw"] = np.clip(
        df["total_63kv_bus_mw"] - df["cat_generation_63kv_mw"], 5.0, 60.0
    ).round(3)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3 — Air comprimé (7 bars et 3 bars)
# ─────────────────────────────────────────────────────────────────────────────

def generate_air_data(df: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """
    Ajoute les colonnes air comprimé 7 bars et 3 bars.

    7 bars : C713/C714 toujours en marche, C715/C717 selon production,
             C716 en secours (démarrage > 90 % de charge).
    3 bars : C321-C323 (VSD) absorbent la demande transport ;
             C311/C312 (fixes) restent à l'arrêt en nominal.
    """
    rng = _rng(seed + 200)
    n = len(df)
    prod = df["production_index"].values
    hours = (
        pd.to_datetime(df["timestamp"]).dt.hour
        + pd.to_datetime(df["timestamp"]).dt.minute / 60.0
    ).values

    # ── Air 7 bars ────────────────────────────────────────────────────────
    total_7b_flow = np.zeros(n)
    total_7b_power = np.zeros(n)

    for name, thresh in _C7_RUN_THRESH.items():
        running = prod >= thresh

        # Facteur de charge : 0.78 au seuil, jusqu'à 0.96 à pleine production
        denom = max(1.0 - thresh, 0.01)
        load = np.where(
            running,
            np.clip(0.78 + 0.18 * (prod - thresh) / denom, 0.78, 0.97),
            0.0,
        )

        flow = np.where(
            running,
            np.clip(_C7_NOM_FLOW * load + rng.normal(0.0, 14.0, n), 0.0, _C7_NOM_FLOW * 1.01),
            0.0,
        )
        # Puissance légèrement sous-linéaire par rapport au débit
        power = np.where(
            running,
            np.clip(_C7_NOM_POWER * load ** 0.88 + rng.normal(0.0, 1.8, n), 0.0, _C7_NOM_POWER * 1.02),
            0.0,
        )

        df[f"{name}_flow_nm3h"] = flow.round(0)
        df[f"{name}_power_kw"] = power.round(1)
        total_7b_flow += flow
        total_7b_power += power

    df["air_7b_total_flow_nm3h"] = total_7b_flow.round(0)
    df["air_7b_total_power_kw"] = total_7b_power.round(1)

    # Pression : 7,0 bar ± 0,1 — légèrement plus basse à fort débit
    nom_cap_7b = float(_C7_NOM_FLOW * 5)
    flow_ratio_7b = total_7b_flow / nom_cap_7b
    pressure_7b = 7.05 - 0.22 * (flow_ratio_7b - 0.55) + rng.normal(0.0, 0.025, n)
    df["air_7b_pressure"] = np.clip(pressure_7b, 6.65, 7.50).round(3)

    # Énergie spécifique (kWh/Nm³) — toujours calculable car C713+C714 tournent
    df["air_7b_specific_energy_kwh_per_nm3"] = np.where(
        total_7b_flow > 100,
        np.clip(total_7b_power / total_7b_flow, 0.088, 0.130),
        0.0,
    ).round(4)

    # ── Air 3 bars ────────────────────────────────────────────────────────
    # Demande pilotée par l'activité transport
    dust_base = _day_factor(hours, base=0.28, peak=0.88)
    coal_base = _day_factor(hours, base=0.18, peak=0.72)

    df["dust_transport_index"] = np.clip(
        dust_base + rng.normal(0.0, 0.04, n), 0.0, 1.0
    ).round(3)
    df["coal_transport_index"] = np.clip(
        coal_base + rng.normal(0.0, 0.03, n), 0.0, 1.0
    ).round(3)

    demand = (
        0.50 * df["dust_transport_index"].values
        + 0.50 * df["coal_transport_index"].values
    )

    # VSD : C321 leader, C322 suiveur, C323 modulation
    c321_spd = np.clip(0.52 + 0.46 * demand + rng.normal(0.0, 0.015, n), 0.25, 1.00)
    c322_spd = np.clip(0.38 + 0.57 * demand + rng.normal(0.0, 0.018, n), 0.10, 1.00)
    c323_spd = np.clip(-0.15 + 0.90 * demand + rng.normal(0.0, 0.022, n), 0.00, 1.00)

    total_3b_flow = np.zeros(n)
    total_3b_power = np.zeros(n)

    for name, spd in [("C321", c321_spd), ("C322", c322_spd), ("C323", c323_spd)]:
        df[f"{name}_speed_pct"] = (spd * 100.0).round(1)
        flow_v = np.clip(_C3_VAR_MAX_FLOW * spd + rng.normal(0.0, 7.0, n), 0.0, _C3_VAR_MAX_FLOW * 1.01)
        # Puissance VSD : pertes fixes + part variable
        power_v = np.clip(
            _C3_VAR_MAX_POWER * (0.12 + 0.88 * spd) + rng.normal(0.0, 1.0, n),
            0.0, _C3_VAR_MAX_POWER * 1.02,
        )
        df[f"{name}_power_kw"] = power_v.round(1)
        total_3b_flow += flow_v
        total_3b_power += power_v

    # Fixes : à l'arrêt en nominal
    for name in ("C311", "C312"):
        df[f"{name}_status"] = 0
        df[f"{name}_power_kw"] = 0.0

    df["air_3b_total_flow_nm3h"] = total_3b_flow.round(0)
    df["air_3b_total_power_kw"] = total_3b_power.round(1)

    # Pression 3 bars
    nom_cap_3b = float(_C3_VAR_MAX_FLOW * 3)
    flow_ratio_3b = total_3b_flow / nom_cap_3b
    pressure_3b = 3.06 - 0.20 * (flow_ratio_3b - 0.55) + rng.normal(0.0, 0.018, n)
    df["air_3b_pressure"] = np.clip(pressure_3b, 2.65, 3.40).round(3)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4 — Eau recyclée & eau brute
# ─────────────────────────────────────────────────────────────────────────────

def generate_water_data(df: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """
    Ajoute les colonnes eau recyclée (refroidissement) et eau brute (bassins B0/B1).

    Contraintes :
        delta_t = return_temp − supply_temp > 0
        niveaux bassins ∈ [0 %, 100 %]
        débit appoint ≈ 1,9 % du débit recyclé (évaporation + purge)
    """
    rng = _rng(seed + 300)
    n = len(df)
    prod = df["production_index"].values

    # ── Eau recyclée — demande ────────────────────────────────────────────
    furnace_sum = (
        df["furnace_1_63kv_mw"].values
        + df["furnace_2_63kv_mw"].values
        + df["furnace_3_63kv_mw"].values
    )
    furnace_max = sum(_FURNACE_NOM_MW)

    df["furnace_cooling_demand_index"] = np.clip(
        furnace_sum / furnace_max + rng.normal(0.0, 0.015, n), 0.30, 1.0
    ).round(3)

    df["bearing_cooling_demand_index"] = np.clip(
        0.40 + 0.45 * prod + rng.normal(0.0, 0.025, n), 0.20, 1.0
    ).round(3)

    total_cool = (
        0.65 * df["furnace_cooling_demand_index"].values
        + 0.35 * df["bearing_cooling_demand_index"].values
    )

    # ── Eau recyclée — débit & températures ──────────────────────────────
    df["recycled_water_flow_m3h"] = np.clip(
        _RW_NOM_FLOW * (0.76 + 0.30 * total_cool) + rng.normal(0.0, 7.0, n),
        600, 980,
    ).round(0)

    df["recycled_water_supply_temp_c"] = np.clip(
        _RW_SUPPLY_TEMP + rng.normal(0.0, 0.35, n), 21.0, 27.5
    ).round(2)

    delta_t = np.clip(
        _RW_DELTA_T_NOM * (0.68 + 0.46 * total_cool) + rng.normal(0.0, 0.18, n),
        3.5, 9.5,
    )
    df["recycled_water_delta_t_c"] = delta_t.round(2)
    df["recycled_water_return_temp_c"] = (
        df["recycled_water_supply_temp_c"].values + delta_t
    ).round(2)

    # ── Eau recyclée — équipements ────────────────────────────────────────
    flow_ratio = df["recycled_water_flow_m3h"].values / _RW_NOM_FLOW

    df["recycled_water_pump_power_kw"] = np.clip(
        50.0 + 22.0 * flow_ratio + rng.normal(0.0, 1.0, n), 38.0, 78.0
    ).round(1)

    df["cooling_tower_power_kw"] = np.clip(
        16.0 + 14.0 * total_cool + rng.normal(0.0, 0.7, n), 10.0, 34.0
    ).round(1)

    # ── Eau recyclée — qualité ────────────────────────────────────────────
    return_temp = df["recycled_water_return_temp_c"].values
    df["legionella_risk_index"] = np.clip(
        0.04 + 0.45 * (return_temp - 24.0) / 12.0 + rng.normal(0.0, 0.018, n),
        0.0, 1.0,
    ).round(3)

    # Traitement chimique cyclique (3 dosages / 24 h)
    t_cycle = np.linspace(0, 3 * 2 * np.pi, n)
    df["chemical_treatment_index"] = np.clip(
        0.82 + 0.12 * np.sin(t_cycle) + rng.normal(0.0, 0.025, n), 0.55, 1.0
    ).round(3)

    # ── Eau brute — appoint ───────────────────────────────────────────────
    # Évaporation (~1,4 %) + purge (~0,5 %) = ~1,9 % du débit circulation
    makeup_base = df["recycled_water_flow_m3h"].values * 0.019
    df["raw_water_makeup_to_recycled_m3h"] = np.clip(
        makeup_base + rng.normal(0.0, 1.2, n), 5.0, 35.0
    ).round(1)

    df["raw_water_flow_m3h"] = np.clip(
        df["raw_water_makeup_to_recycled_m3h"].values + rng.normal(0.0, 1.5, n),
        4.0, 38.0,
    ).round(1)

    # ── Eau brute — bassins (marche aléatoire à retour à la moyenne) ──────
    def _basin_walk(
        start: float, mean: float, rng_b: np.random.Generator
    ) -> np.ndarray:
        lvl = np.empty(n)
        lvl[0] = start
        for i in range(1, n):
            rev = 0.006 * (mean - lvl[i - 1])
            lvl[i] = np.clip(lvl[i - 1] + rev + rng_b.normal(0.0, 0.12), 5.0, 97.0)
        return lvl

    b0 = _basin_walk(72.0, 68.0, _rng(seed + 351))
    b1 = _basin_walk(58.0, 62.0, _rng(seed + 361))

    df["basin_b0_level_pct"] = np.round(b0, 1)
    df["basin_b1_level_pct"] = np.round(b1, 1)
    df["basin_b0_volume_m3"] = (b0 / 100.0 * _B0_CAPACITY_M3).round(0)
    df["basin_b1_volume_m3"] = (b1 / 100.0 * _B1_CAPACITY_M3).round(0)

    df["emergency_cooling_available"] = (
        (df["basin_b0_level_pct"] > 20.0) | (df["basin_b1_level_pct"] > 20.0)
    )

    # Capacité sécurité : ~45 % du volume stocké total / heure
    stored = (
        b0 / 100.0 * _B0_CAPACITY_M3
        + b1 / 100.0 * _B1_CAPACITY_M3
    )
    df["emergency_cooling_capacity_m3h"] = np.clip(stored * 0.45, 0.0, 1_500.0).round(0)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5 — Point d'entrée principal
# ─────────────────────────────────────────────────────────────────────────────

def generate_mock_plant_data(seed: int = SEED) -> pd.DataFrame:
    """
    Génère le DataFrame complet de l'usine (96 lignes × ~60 colonnes).

    Ordre de construction :
        1. Timeline + production_index
        2. Électricité
        3. Air comprimé (7 bars + 3 bars)
        4. Eau recyclée + eau brute

    Returns
    -------
    pd.DataFrame
        Toutes les colonnes utilities sur 24 h à pas de 15 min.
    """
    df = generate_base_timeseries(seed)
    df = generate_electricity_data(df, seed)
    df = generate_air_data(df, seed)
    df = generate_water_data(df, seed)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Script de validation rapide
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = generate_mock_plant_data()

    print("─" * 60)
    print(f"Shape              : {df.shape}")
    print(f"Colonnes           : {len(df.columns)}")
    print("─" * 60)

    print("\n── df.head() ──")
    print(df[["timestamp", "production_index",
              "total_63kv_bus_mw", "air_7b_pressure",
              "air_3b_pressure", "recycled_water_flow_m3h",
              "basin_b0_level_pct", "basin_b1_level_pct"]].head(8).to_string(index=False))

    print("\n── Colonnes ──")
    for col in df.columns:
        print(f"  {col}")

    print("\n── df.describe() (sélection) ──")
    cols_describe = [
        "production_index",
        "total_63kv_bus_mw", "cat_generation_63kv_mw", "grid_import_63kv_mw",
        "air_7b_pressure", "air_7b_total_flow_nm3h", "air_7b_specific_energy_kwh_per_nm3",
        "air_3b_pressure", "air_3b_total_flow_nm3h",
        "recycled_water_flow_m3h", "recycled_water_return_temp_c",
        "basin_b0_level_pct", "basin_b1_level_pct",
    ]
    print(df[cols_describe].describe().round(3).to_string())

    print("\n── Pressions air ──")
    print(f"  7 bars  min={df['air_7b_pressure'].min():.3f}  max={df['air_7b_pressure'].max():.3f} bar")
    print(f"  3 bars  min={df['air_3b_pressure'].min():.3f}  max={df['air_3b_pressure'].max():.3f} bar")

    print("\n── Puissances ──")
    print(f"  Total 63kV bus  min={df['total_63kv_bus_mw'].min():.1f}  max={df['total_63kv_bus_mw'].max():.1f} MW")
    print(f"  CAT génération  min={df['cat_generation_63kv_mw'].min():.1f}  max={df['cat_generation_63kv_mw'].max():.1f} MW")
    print(f"  Importation     min={df['grid_import_63kv_mw'].min():.1f}  max={df['grid_import_63kv_mw'].max():.1f} MW")

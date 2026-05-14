import json, math, pathlib

EPS0 = 8.8541878128e-12  # vacuum permittivity

def load_maxwell_pack(path="backend/modules/dimensions/containers/kg_exports/maxwell_core.kg.json"):
    p = pathlib.Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def has_gauss_law(pack):
    for link in pack.get("links", []):
        if "div_E" in (link.get("relation") or "") and "ρ/ε0" in link["relation"]:
            return True
    return False

def E_of_point_charge(q_coulomb: float, r_meters: float) -> float:
    # |E| = q / (4π ε0 r^2)
    return q_coulomb / (4 * math.pi * EPS0 * (r_meters ** 2))

if __name__ == "__main__":
    pack = load_maxwell_pack()
    print("Gauss law present:", has_gauss_law(pack))
    # toy check: field at 1m from 1 nC
    E = E_of_point_charge(1e-9, 1.0)
    print("E(1nC, 1m) ~", E, "V/m")
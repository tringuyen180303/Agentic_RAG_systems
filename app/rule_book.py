######################################################################
# 0. load YAML once
######################################################################
import re, yaml, pathlib
from typing import Dict, List
from langchain.tools import Tool
import json
RULES = yaml.safe_load(pathlib.Path("docs/rule_book.yaml").read_text())

######################################################################
# 1.  FLUID regex – handles dot-and-no-dot flavours
######################################################################
FLUID = r"""
    (?P<vis1>\d+Ø?)              # 1st viscosity (required)
    (?: / (?P<vis2>\d+Ø?) )?     # optional 2nd viscosity
    (?P<unit>CS|C|V)             # unit (CS before C!)
    \.?                          # 0 or 1 dot before SG
    (?P<sg>\d+(?:\.\d+)?)        # SG digits (e.g. 9   or 1.05)
"""

FLOW_UNITS = "|".join(RULES["max_flow_ranges"].keys())          # → GM|LM|CMH|GLM|DGM

# (a) loose pattern
TOKENS = re.compile(
    rf"""
    (?P<series>MN|MM|MH|SN|SM|SH)?    -?
    (?P<housing>[A-Z])?              -?
    (?P<internals>[A-Z])?            -?
    (?P<seal>[A-Z])?                 -?
    (?P<flow_num>\d+)?               # NEW – digits only
    (?P<flow_unit>[A-Z]+)?           # NEW – letters only
    -?
    (?P<port>[0-9A-Z]*)              # may be blank
    (?P<valve>-V)?                   -?
    (?P<fluid>{FLUID})?              # optional
    """,
    re.VERBOSE,
)

# (b) strict pattern
STRICT = re.compile(
    rf"""
    (?P<series>MN|MM|MH|SN|SM|SH)
    -?
    (?P<housing>[ABDIFM])
    (?P<internals>[IT])
    (?P<seal>[BFK])
    (?P<flow_num>\d+)
    (?P<flow_unit>{FLOW_UNITS})      # only the legal units
    -?
    (?P<port>[0-9A-Z]+)
    (?P<valve>-V)?
    -?
    (?P<fluid>{FLUID})
    """,
    re.VERBOSE,
)
######################################################################
# 3.  human-friendly helper messages
######################################################################
def _fmt_choices(keys) -> str:
    """Pretty-print {A,B,C} with thin spaces after commas."""
    return "{ " + ", ".join(keys) + " }"

def suggest_housing() -> str:
    codes = RULES["housing_materials"].keys()          # e.g. dict_keys(['A','B',…])
    return f"Choose housing ∈ {_fmt_choices(codes)}"

def suggest_internals() -> str:
    parts = RULES["internal_parts"]                    # {I: "316 SS", T: "Titanium"}
    desc  = "; ".join(f"{k} = {v}" for k, v in parts.items())
    return f"Internals must be one of {_fmt_choices(parts)}  ({desc})"

def suggest_seal() -> str:
    seals = RULES["seal_materials"]
    desc  = "; ".join(f"{k} = {v}" for k, v in seals.items())
    return f"Seal must be one of {_fmt_choices(seals)}  ({desc})"

def suggest_flow() -> str:
    units = ", ".join(RULES["max_flow_ranges"].keys())
    return f"Add the max-flow segment: <digits><unit> where <unit> ∈ {{ {units} }}"

def suggest_port(flow_gpm: int) -> str:
    valid = [c for c, m in RULES["ports"]["threaded"].items()
             if flow_gpm <= m["max_gpm"]]
    return f"Valid port codes for {flow_gpm} GPM → {', '.join(valid)}"

######################################################################
# 4.  validator
######################################################################
def explain_code(code: str) -> dict:
    """Return {'verdict', 'errors', 'suggestions'}."""
    code = code.strip()

    # fast path
    if STRICT.fullmatch(code):
        return {"verdict": "VALID", "errors": [], "suggestions": []}

    m = TOKENS.fullmatch(code)
    if not m:          # looks nothing like a meter code
        return {
            "verdict": "INVALID",
            "errors": ["code does not look like an MN/MM/MH/SN/SM/SH flow-meter part"],
            "suggestions": ["Format: MN/SN-<housing><internals><seal><flow>-<port>[-V]<fluid>"],
        }

    g, errs, sugg = m.groupdict(), [], []

    # ── series ───────────────────────────────────────────────────────
    if not g["series"]:
        errs.append("missing series (MN/MM/MH)")

    # ── housing ──────────────────────────────────────────────────────
    h = g["housing"]
    if not h:               errs.append("missing housing"); sugg.append(suggest_housing())
    elif h not in RULES["housing_materials"]:
        errs.append(f"unknown housing '{h}'"); sugg.append(suggest_housing())

    # ── internals ────────────────────────────────────────────────────
    i = g["internals"]
    if not i:                errs.append("missing internals"); sugg.append(suggest_internals())
    elif i not in RULES["internal_parts"]:
        errs.append(f"invalid internals '{i}'"); sugg.append(suggest_internals())

    # ── seal ─────────────────────────────────────────────────────────
    s = g["seal"]
    if not s:                errs.append("missing seal"); sugg.append(suggest_seal())
    elif s not in {"B", "F", "K"}:
        errs.append(f"invalid seal '{s}'"); sugg.append(suggest_seal())

    # ── flow / port checks ───────────────────────────────────────────
    flow_num  = g["flow_num"]
    flow_unit = g["flow_unit"]

    if not flow_num or not flow_unit:
        errs.append("missing max-flow segment (<digits><unit>)")
        sugg.append(suggest_flow())

    elif flow_unit not in RULES["max_flow_ranges"]:
        errs.append(f"unknown flow unit '{flow_unit}'")
        sugg.append(suggest_flow())

    else:
        flow_val = int(flow_num)                    # ← derived from *num* only

        port = g["port"]
        if not port:
            errs.append("missing port code")
            sugg.append(suggest_port(flow_val))
        else:
            limit = RULES["ports"]["threaded"].get(port, {}).get("max_gpm")
            if limit is None:
                errs.append(f"unknown port '{port}'")
                sugg.append(suggest_port(flow_val))
            elif flow_val > limit:
                errs.append(f"{flow_val} GPM exceeds port '{port}' limit {limit}")
                sugg.append(suggest_port(flow_val))
        # ── fluid spec ───────────────────────────────────────────────────
        if not g["fluid"]:
            errs.append("missing viscosity / SG block (e.g. 32V.9)")

    # ── final verdict ────────────────────────────────────────────────
    return {"verdict": "INVALID", "errors": errs, "suggestions": sugg}

######################################################################
# 5.  LangChain tool wrapper
######################################################################
# def consult_and_explain(inp: str) -> str:
#     res = explain_code(inp)
#     if res["verdict"] == "VALID":
#         return "✅ VALID"

#     body  = "❌ INVALID\n" + "\n".join(f"- {e}" for e in res["errors"])
#     if res["suggestions"]:
#         body += "\n\nSuggestions:\n" + "\n".join(f"* {s}" for s in res["suggestions"])
#     return body

def consult_and_explain(code: str) -> str:
    res = explain_code(code)        # ➟ your existing validator
    if res["verdict"] == "VALID":
        payload = {"valid": True, "errors": [], "suggestions": []}
    else:
        payload = {
            "valid": False,
            "errors": res["errors"],          # list[str]
            "suggestions": res["suggestions"] # list[str]
        }
    return json.dumps(payload, ensure_ascii=False) 

rulebook_tool = Tool(
    name        = "RuleBook",
    func        = consult_and_explain,
    description = "Validate a flow-meter model code and return JSON with fields: valid, errors, suggestions..",
)


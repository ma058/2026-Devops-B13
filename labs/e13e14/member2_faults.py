"""Select a narrowly scoped failure injection for one four-role deployment."""
SCENARIOS = ("normal", "C4", "C5")
FAULT_ROLES = {"normal": (), "C4": ("draft",), "C5": ("draft", "mdfixer")}


def fault_environment(role, scenario):
    enabled = role in FAULT_ROLES[scenario]
    return {
        "E14_ENABLE_FAULTS": "1" if enabled else "0",
        "E14_FAULT_SCENARIO": scenario if enabled else "normal",
    }


def permits_fault(kind, env):
    return (kind in ("C4", "C5")
            and env.get("E14_ENABLE_FAULTS") == "1"
            and env.get("E14_FAULT_SCENARIO") == kind)

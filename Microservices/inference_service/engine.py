"""
Inference Engine — Steps 3, 4 & 5
===================================
Loads the ONNX model and calibration data once at startup.
Runs the forward pass, applies isotonic calibration, and generates
the assessment report narrative.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

_models_dir = Path(__file__).resolve().parent / "models"
ONNX_MODEL_PATH = _models_dir / "icu_model.onnx"
CALIBRATION_PATH = _models_dir / "calibration.json"

# ── Module-level singletons (loaded once) ───────────────────────────
_session: ort.InferenceSession | None = None
_calibration: dict | None = None


def load_model() -> None:
    """Load ONNX model and calibration JSON into memory."""
    global _session, _calibration

    if not ONNX_MODEL_PATH.exists():
        raise FileNotFoundError(f"ONNX model not found at {ONNX_MODEL_PATH}")
    if not CALIBRATION_PATH.exists():
        raise FileNotFoundError(f"Calibration file not found at {CALIBRATION_PATH}")

    logger.info(f"[ENGINE] Loading ONNX model from {ONNX_MODEL_PATH}")
    _session = ort.InferenceSession(
        str(ONNX_MODEL_PATH),
        providers=["CPUExecutionProvider"],
    )

    logger.info(f"[ENGINE] Loading calibration from {CALIBRATION_PATH}")
    with open(CALIBRATION_PATH, "r") as f:
        _calibration = json.load(f)

    logger.info("[ENGINE] Model and calibration loaded successfully.")


def _get_session() -> ort.InferenceSession:
    if _session is None:
        load_model()
    return _session


def _get_calibration() -> dict:
    if _calibration is None:
        load_model()
    return _calibration


# ── Step 4: Isotonic Calibration ────────────────────────────────────

def _calibrate(raw_value: float, isotonic_X: list, isotonic_y: list) -> float:
    """Apply isotonic calibration via np.interp."""
    return float(np.interp(raw_value, isotonic_X, isotonic_y))


# ── Step 5: Qualitative Band Assignment ─────────────────────────────

def _band(prob: float) -> str:
    if prob < 0.20:
        return "low"
    elif prob < 0.50:
        return "moderate"
    elif prob < 0.75:
        return "high"
    else:
        return "critical"


def _generate_report(
    visit_id: str,
    n: int,
    mortality_prob: float,
    global_sev_prob: float,
    vent_prob: float,
    cardiac_prob: float,
    mechanical_prob: float,
    dialysis_prob: float,
) -> str:
    """Step 5: Generate natural language narrative."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"Severity assessment S{n} for stay {visit_id}, computed at {now} "
        f"using {n} of 6 windows.\n\n"
        f"Mortality risk: {mortality_prob*100:.1f}% ({_band(mortality_prob)}).\n"
        f"Global severity score: {global_sev_prob*100:.1f}% ({_band(global_sev_prob)}).\n\n"
        f"Intervention probabilities:\n"
        f"  - Mechanical ventilation: {vent_prob*100:.1f}% ({_band(vent_prob)})\n"
        f"  - Cardiac support: {cardiac_prob*100:.1f}% ({_band(cardiac_prob)})\n"
        f"  - Mechanical support: {mechanical_prob*100:.1f}% ({_band(mechanical_prob)})\n"
        f"  - Dialysis: {dialysis_prob*100:.1f}% ({_band(dialysis_prob)})"
    )


def _clean(val: float) -> float:
    """Ensure value is a finite float (not NaN or Inf) for JSON compatibility."""
    if np.isnan(val) or np.isinf(val):
        return 0.0
    return float(val)


# ── Main Inference Pipeline ─────────────────────────────────────────

def run_inference(
    inputs: dict[str, np.ndarray],
    severity_index: int,
    visit_id: str,
) -> dict:
    """
    Steps 3-5: Run ONNX forward pass, calibrate, generate report.

    Parameters
    ----------
    inputs : dict
        ONNX-ready tensors from tensor_builder.
    severity_index : int
        n — the number of populated windows.
    visit_id : str
        Zero-padded visit ID.

    Returns
    -------
    dict with all fields needed for InferenceResponse.
    """
    session = _get_session()
    calibration = _get_calibration()

    # Step 3: ONNX forward pass
    input_feed = {inp.name: inputs[inp.name] for inp in session.get_inputs()}
    raw_outputs = session.run(None, input_feed)

    # Map output names to arrays
    output_names = [o.name for o in session.get_outputs()]
    output_dict = dict(zip(output_names, raw_outputs))

    # Extract position n-1 (latest populated window)
    pos = severity_index - 1

    raw_mortality = float(output_dict["mortality_prob"][0, pos, 0])
    raw_severity = float(output_dict["severity_score"][0, pos, 0])

    # Interventions: [1, 6, 5] → [vent, dialysis, mechanical, cardiac, global_sev]
    interventions = output_dict["interventions"][0, pos]  # shape (5,)
    raw_vent = float(interventions[0])
    raw_dialysis = float(interventions[1])
    raw_mechanical = float(interventions[2])
    raw_cardiac = float(interventions[3])
    raw_global_sev = float(interventions[4])

    # Step 4: Isotonic calibration
    cal_key = f"S{severity_index}"
    cal = calibration[cal_key]

    mortality_prob = _calibrate(raw_mortality, cal["mortality"]["isotonic_X"], cal["mortality"]["isotonic_y"])
    severity_score = _calibrate(raw_severity, cal["severity_score"]["isotonic_X"], cal["severity_score"]["isotonic_y"])
    vent_prob = _calibrate(raw_vent, cal["interventions"]["ventilation"]["isotonic_X"], cal["interventions"]["ventilation"]["isotonic_y"])
    dialysis_prob = _calibrate(raw_dialysis, cal["interventions"]["dialysis"]["isotonic_X"], cal["interventions"]["dialysis"]["isotonic_y"])
    mechanical_prob = _calibrate(raw_mechanical, cal["interventions"]["mechanical"]["isotonic_X"], cal["interventions"]["mechanical"]["isotonic_y"])
    cardiac_prob = _calibrate(raw_cardiac, cal["interventions"]["cardiac"]["isotonic_X"], cal["interventions"]["cardiac"]["isotonic_y"])
    global_sev_prob = _calibrate(raw_global_sev, cal["interventions"]["global_sev"]["isotonic_X"], cal["interventions"]["global_sev"]["isotonic_y"])

    # Step 5: Generate narrative report
    assessment_report = _generate_report(
        visit_id, severity_index,
        mortality_prob, global_sev_prob,
        vent_prob, cardiac_prob, mechanical_prob, dialysis_prob,
    )

    assessment_id = str(uuid.uuid4())

    logger.info(
        f"[ENGINE] visit={visit_id} S{severity_index}: "
        f"mortality={mortality_prob:.3f} severity={severity_score:.3f} "
        f"global_sev={global_sev_prob:.3f}"
    )

    return {
        "assessment_id": assessment_id,
        "visit_id": visit_id,
        "severity_index": severity_index,
        "mortality_prob": _clean(round(mortality_prob, 6)),
        "severity_score": _clean(round(severity_score, 6)),
        "vent_prob": _clean(round(vent_prob, 6)),
        "dialysis_prob": _clean(round(dialysis_prob, 6)),
        "mechanical_prob": _clean(round(mechanical_prob, 6)),
        "cardiac_prob": _clean(round(cardiac_prob, 6)),
        "global_sev_prob": _clean(round(global_sev_prob, 6)),
        "assessment_report": assessment_report,
    }

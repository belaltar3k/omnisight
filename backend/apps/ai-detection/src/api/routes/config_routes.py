from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/config")

_config = None
_model_manager = None
_worker_pool = None


def init_config_routes(config, model_manager, worker_pool):
    global _config, _model_manager, _worker_pool
    _config = config
    _model_manager = model_manager
    _worker_pool = worker_pool


class ConfigUpdate(BaseModel):
    disabled_models: Optional[list[str]] = None
    disabled_sa_modules: Optional[list[str]] = None
    weights: Optional[dict[str, float]] = None
    anomaly_threshold: Optional[float] = None


@router.get("")
async def get_config():
    active = _model_manager.get_active_names() if _model_manager else []
    return {
        "device": _config.DEVICE,
        "anomaly_threshold": _config.ANOMALY_THRESHOLD,
        "fusion_interval": _config.FUSION_INTERVAL,
        "target_fps": _config.TARGET_FPS,
        "min_anomaly_duration": _config.MIN_ANOMALY_DURATION,
        "dominance_weight": _config.DOMINANCE_WEIGHT,
        "smoothing_window": _config.SMOOTHING_WINDOW,
        "weights": _config.get_weights_dict(),
        "disabled_models": _config.DISABLED_MODELS,
        "disabled_sa_modules": _config.DISABLED_SA_MODULES,
        "active_detectors": active,
    }


@router.patch("")
async def update_config(update: ConfigUpdate):
    changes = []

    if update.disabled_models is not None:
        previously_disabled = set(_config.DISABLED_MODELS)
        new_disabled = set(update.disabled_models)

        for name in new_disabled - previously_disabled:
            if _model_manager.disable_detector(name):
                changes.append(f"disabled {name}")
        for name in previously_disabled - new_disabled:
            if _model_manager.enable_detector(name):
                changes.append(f"enabled {name}")

        _config.DISABLED_MODELS = list(new_disabled)

    if update.disabled_sa_modules is not None:
        _config.DISABLED_SA_MODULES = list(update.disabled_sa_modules)
        changes.append(f"updated SA modules: disabled={update.disabled_sa_modules}")

    if update.weights is not None:
        for key, value in update.weights.items():
            attr = f"WEIGHT_{key.upper().replace('CRIME_', '')}"
            if key == "crime_skelnet":
                attr = "WEIGHT_SKELNET"
            elif key == "weapon_detection":
                attr = "WEIGHT_WEAPON"
            elif key == "video_mae":
                attr = "WEIGHT_VIDEOMAE"
            elif key == "surveillance_analytics":
                attr = "WEIGHT_SURVEILLANCE"
            elif key == "paan":
                attr = "WEIGHT_PAAN"

            if hasattr(_config, attr):
                setattr(_config, attr, value)

        if _worker_pool:
            for pipeline in _worker_pool._pipelines.values():
                pipeline.fusion.update_weights(_config.get_weights_dict())

        changes.append(f"updated weights: {update.weights}")

    if update.anomaly_threshold is not None:
        _config.ANOMALY_THRESHOLD = update.anomaly_threshold
        if _worker_pool:
            for pipeline in _worker_pool._pipelines.values():
                pipeline.fusion.anomaly_threshold = update.anomaly_threshold
        changes.append(f"threshold={update.anomaly_threshold}")

    return {"success": True, "changes": changes}

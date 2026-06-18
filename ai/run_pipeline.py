#!/usr/bin/env python3
"""Run the OmniSight anomaly-detection pipeline on a video file."""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniSight anomaly-detection pipeline")
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument("--output-dir", default="pipeline_output", help="Directory for outputs")
    parser.add_argument("--threshold", type=float, default=0.55, help="Anomaly threshold")
    parser.add_argument("--device", default="cuda", help="Torch device (cuda / cpu)")
    parser.add_argument("--disable", nargs="+", default=[], help="Component names to skip")
    parser.add_argument("--weights-dir", default=None, help="Base directory for model weights")
    parser.add_argument("--no-plot", action="store_true", help="Skip generating the anomaly plot")
    parser.add_argument("--no-video", action="store_true", help="Skip generating annotated output video")
    parser.add_argument("--json", dest="json_path", default=None, help="Save JSON summary to file")
    parser.add_argument("--enable-analytics", action="store_true", help="Enable the surveillance_analytics component")
    parser.add_argument("--analytics-only", action="store_true", help="Run ONLY surveillance_analytics and disable everything else")
    args = parser.parse_args()
    
    if args.analytics_only:
        args.enable_analytics = True
        for comp in ["crime_skelnet", "weapon_detection", "video_mae", "paan"]:
            if comp not in args.disable:
                args.disable.append(comp)
                
    if not args.enable_analytics:
        args.disable.append("surveillance_analytics")

    ai_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(ai_dir)
    if ai_dir not in sys.path:
        sys.path.insert(0, ai_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from pipeline import PipelineConfig, PipelineRunner, render_video

    weights_dir = args.weights_dir or os.path.join(ai_dir, "weights")

    config = PipelineConfig(
        anomaly_threshold=args.threshold,
        device=args.device,
        disabled=args.disable,
        video_mae_weights=os.path.join(weights_dir, "video_mae", "best_model_higher_94.pth"),
        skelnet_weights=os.path.join(weights_dir, "crime_skelnet", "best_anomaly_skel.pth"),
        weapon_weights=os.path.join(weights_dir, "weapon_detection", "best.pt"),
        pose_model=os.path.join(ai_dir, "yolov8x-pose.pt"),
    )

    runner = PipelineRunner(config)
    result = runner.run(args.video)

    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Video duration : {result.duration:.1f}s  ({result.num_frames} frames @ {result.fps:.1f} FPS)")
    print(f"  Processing time: {result.processing_time:.1f}s")
    print(f"  Threshold      : {result.threshold}")
    print(f"  Peak fused score: {result.peak_score:.4f}")
    print(f"  Anomalous      : {result.is_anomalous}")

    if result.disabled_components:
        print(f"  Disabled       : {', '.join(result.disabled_components)}")
    if result.failed_components:
        print(f"  Failed         : {result.failed_components}")

    print("\nComponent Scores:")
    for name, scores in result.component_scores.items():
        w = result.active_weights.get(name, 0)
        print(f"  {name:20s}  weight={w:.2f}  peak={scores.max():.4f}  mean={scores.mean():.4f}")

    if result.anomaly_regions:
        print(f"\nAnomaly Regions ({len(result.anomaly_regions)}):")
        for i, r in enumerate(result.anomaly_regions, 1):
            print(f"  [{i}] {r.start_time:.1f}s – {r.end_time:.1f}s  "
                  f"(frames {r.start_frame}–{r.end_frame})  "
                  f"peak={r.peak_score:.3f}  mean={r.mean_score:.3f}")
    else:
        print("\nNo anomaly regions detected.")

    crime_class = result.component_metadata.get("video_mae", {}).get("crime_class")
    if crime_class:
        print(f"\nVideoMAE crime class: {crime_class}")

    surveillance_stats = result.component_metadata.get("surveillance_analytics", {}).get("stats")
    if surveillance_stats:
        print(f"\nSurveillance Analytics Stats:")
        for k, v in surveillance_stats.items():
            print(f"  {k:15s}: {v}")

    os.makedirs(args.output_dir, exist_ok=True)

    if not args.no_video:
        video_out = os.path.join(args.output_dir, "annotated_output.mp4")
        render_video(args.video, result, video_out)

    if not args.no_plot:
        _save_plot(result, args.output_dir)

    if args.json_path:
        _save_json(result, args.json_path)

    print(f"\nOutputs saved to {os.path.abspath(args.output_dir)}/")


def _save_plot(result, output_dir: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[Plot] matplotlib not installed — skipping plot.")
        return

    time_axis = np.linspace(0, result.duration, result.num_frames)

    fig, ax = plt.subplots(figsize=(14, 5))

    colors = {
        "crime_skelnet": "#2196F3",
        "video_mae": "#FF9800",
        "weapon_detection": "#F44336",
        "paan": "#4CAF50",
    }

    for name, scores in result.component_scores.items():
        w = result.active_weights.get(name, 0)
        color = colors.get(name, "#999999")
        ax.plot(time_axis, scores, label=f"{name} (w={w:.2f})", alpha=0.5, linewidth=1, color=color)

    ax.plot(time_axis, result.fused_scores, label="Fused", color="black", linewidth=2)
    ax.axhline(y=result.threshold, color="red", linestyle="--", linewidth=1, label=f"Threshold ({result.threshold})")

    for region in result.anomaly_regions:
        ax.axvspan(region.start_time, region.end_time, alpha=0.15, color="red")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Anomaly Score")
    ax.set_title("OmniSight Pipeline — Anomaly Scores")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    plot_path = os.path.join(output_dir, "anomaly_scores.png")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"[Plot] Saved to {plot_path}")


def _save_json(result, json_path: str) -> None:
    summary = {
        "num_frames": result.num_frames,
        "fps": result.fps,
        "duration": result.duration,
        "threshold": result.threshold,
        "is_anomalous": result.is_anomalous,
        "peak_score": result.peak_score,
        "processing_time": result.processing_time,
        "active_weights": result.active_weights,
        "disabled_components": result.disabled_components,
        "failed_components": result.failed_components,
        "component_peaks": {
            name: float(scores.max()) for name, scores in result.component_scores.items()
        },
        "anomaly_regions": [
            {
                "start_frame": r.start_frame,
                "end_frame": r.end_frame,
                "start_time": round(r.start_time, 2),
                "end_time": round(r.end_time, 2),
                "peak_score": round(r.peak_score, 4),
                "mean_score": round(r.mean_score, 4),
            }
            for r in result.anomaly_regions
        ],
    }

    crime_class = result.component_metadata.get("video_mae", {}).get("crime_class")
    if crime_class:
        summary["crime_class"] = crime_class

    surveillance_stats = result.component_metadata.get("surveillance_analytics", {}).get("stats")
    if surveillance_stats:
        summary["surveillance_stats"] = surveillance_stats

    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[JSON] Saved to {json_path}")


if __name__ == "__main__":
    main()

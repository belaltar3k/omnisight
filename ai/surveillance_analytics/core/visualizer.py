from __future__ import annotations

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo


SEVERITY_COLORS = {
    "critical": (0, 0, 255),
    "high":     (0, 80, 255),
    "warning":  (0, 200, 255),
    "info":     (200, 200, 0),
}

ZONE_COLORS = {
    "road":       (255, 100, 0),
    "sidewalk":   (0, 200, 100),
    "crosswalk":  (0, 255, 255),
    "no_parking": (0, 0, 255),
    "restricted": (128, 0, 255),
    "checkout":   (255, 200, 0),
    "entrance":   (0, 255, 0),
}


class Visualizer:
    def __init__(self, config):
        self.config = config
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        self._font_small = cv2.FONT_HERSHEY_PLAIN

    def draw(
        self,
        frame: np.ndarray,
        module_results: dict,
        tracks: dict[int, TrackInfo],
        recent_alerts: list[dict],
        show_heatmap: bool = False,
        show_zones: bool = True,
        show_alerts: bool = True,
        fps: float = 0.0,
        frame_num: int = 0,
        total_frames: int = 0,
    ) -> np.ndarray:
        display = frame.copy()

        if show_zones:
            self._draw_zones(display)

        if show_heatmap:
            heatmap_result = module_results.get("activity_heatmap", {})
            overlay = heatmap_result.get("heatmap_overlay")
            if overlay is not None:
                mask = overlay.sum(axis=2) > 30
                blended = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
                display[mask] = blended[mask]

        self._draw_tracks(display, tracks, module_results)
        self._draw_counting_lines(display, module_results)
        self._draw_congestion_indicator(display, module_results)
        self._draw_stats_panel(display, module_results, tracks, fps, frame_num, total_frames)

        if show_alerts and recent_alerts:
            self._draw_alert_ticker(display, recent_alerts)

        self._draw_branding(display)

        return display

    def _draw_zones(self, display: np.ndarray):
        overlay = display.copy()
        for zone_name, points in self.config.zones.items():
            pts = np.array(points, dtype=np.int32)
            color = ZONE_COLORS.get(zone_name, (128, 128, 128))
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(display, [pts], True, color, 2)
            cx = int(np.mean([p[0] for p in points]))
            cy = int(np.mean([p[1] for p in points]))
            cv2.putText(display, zone_name, (cx - 30, cy), self._font_small, 1.0, (255, 255, 255), 1)
        cv2.addWeighted(overlay, 0.15, display, 0.85, 0, display)

    def _draw_tracks(self, display: np.ndarray, tracks: dict[int, TrackInfo], module_results: dict):
        speed_data = module_results.get("speed_statistics", {}).get("vehicle_speeds", {})

        for tid, track in tracks.items():
            x1, y1, x2, y2 = track.bbox

            if track.class_id == PERSON_CLASS_ID:
                color = (0, 255, 0)
                label = f"P{tid}"
            elif track.class_id in VEHICLE_CLASS_IDS:
                color = (255, 180, 0)
                label = f"V{tid}"
                if tid in speed_data:
                    spd = speed_data[tid]
                    label += f" {spd:.0f}km/h"
                    if spd > self.config.speed_limit_kmh:
                        color = (0, 120, 255)
            else:
                color = (180, 180, 180)
                label = f"{track.class_name}:{tid}"

            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, self._font_small, 1.0, 1)
            cv2.rectangle(display, (x1, y1 - th - 4), (x1 + tw + 4, y1), color, -1)
            cv2.putText(display, label, (x1 + 2, y1 - 2), self._font_small, 1.0, (0, 0, 0), 1)

    def _draw_counting_lines(self, display: np.ndarray, module_results: dict):
        flow_data = module_results.get("pedestrian_flow", {})
        for line_info in self.config.counting_lines:
            p1 = line_info["p1"]
            p2 = line_info["p2"]
            cv2.line(display, p1, p2, (0, 255, 255), 2)
            name = line_info["name"]
            line_stats = flow_data.get("lines", {}).get(name, {})
            in_count = line_stats.get("in", 0)
            out_count = line_stats.get("out", 0)
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            cv2.putText(display, f"In:{in_count} Out:{out_count}", (mid[0] - 40, mid[1] - 10),
                        self._font_small, 1.0, (0, 255, 255), 1)

    def _draw_congestion_indicator(self, display: np.ndarray, module_results: dict):
        density = module_results.get("traffic_density", {})
        congestion = density.get("congestion_index", 0)
        if congestion > 0:
            h, w = display.shape[:2]
            bar_w = 8
            bar_h = 100
            bx, by = 10, 60
            cv2.rectangle(display, (bx, by), (bx + bar_w, by + bar_h), (50, 50, 50), -1)
            fill_h = int(congestion * bar_h)
            if congestion < 0.5:
                bar_color = (0, 200, 0)
            elif congestion < 0.8:
                bar_color = (0, 200, 255)
            else:
                bar_color = (0, 0, 255)
            cv2.rectangle(display, (bx, by + bar_h - fill_h), (bx + bar_w, by + bar_h), bar_color, -1)
            cv2.putText(display, f"{congestion:.0%}", (bx - 2, by - 5), self._font_small, 0.9, bar_color, 1)

    def _draw_stats_panel(self, display: np.ndarray, module_results: dict, tracks: dict,
                          fps: float, frame_num: int, total_frames: int):
        h, w = display.shape[:2]
        panel_w, panel_h = 220, 200
        px, py = w - panel_w - 10, 10

        overlay = display.copy()
        cv2.rectangle(overlay, (px, py), (px + panel_w, py + panel_h), (20, 20, 40), -1)
        cv2.addWeighted(overlay, 0.7, display, 0.3, 0, display)
        cv2.rectangle(display, (px, py), (px + panel_w, py + panel_h), (80, 80, 120), 1)

        persons = sum(1 for t in tracks.values() if t.class_id == PERSON_CLASS_ID)
        vehicles = sum(1 for t in tracks.values() if t.class_id in VEHICLE_CLASS_IDS)

        crowd = module_results.get("crowd_density", {})
        speed = module_results.get("speed_statistics", {})
        throughput = module_results.get("traffic_throughput", {})
        trend = module_results.get("trend_monitor", {})

        trend_dir = trend.get("person_short_term", {}).get("direction", "")
        trend_arrow = {"increasing": "^", "decreasing": "v", "stable": "="}.get(trend_dir, "")

        lines = [
            f"FPS: {fps:.1f}",
            f"Persons: {crowd.get('current_count', persons)} {trend_arrow}",
            f"Vehicles: {vehicles}",
            f"Avg Speed: {speed.get('mean_speed', 0):.0f} km/h",
            f"Throughput: {throughput.get('vehicles_per_minute_avg', 0):.1f}/min",
            f"Tracks: {len(tracks)}",
            f"Frame: {frame_num}",
        ]
        if total_frames > 0:
            lines.append(f"Progress: {frame_num * 100 // total_frames}%")

        for i, text in enumerate(lines):
            cv2.putText(display, text, (px + 10, py + 22 + i * 22), self._font_small, 1.2, (200, 200, 200), 1)

    def _draw_alert_ticker(self, display: np.ndarray, alerts: list[dict]):
        h, w = display.shape[:2]
        bar_h = min(25 * len(alerts), 120)
        y_start = h - bar_h - 5

        overlay = display.copy()
        cv2.rectangle(overlay, (5, y_start), (w - 5, h - 5), (20, 10, 30), -1)
        cv2.addWeighted(overlay, 0.75, display, 0.25, 0, display)

        for i, alert in enumerate(alerts[:5]):
            sev = alert.get("severity", "info")
            color = SEVERITY_COLORS.get(sev, (200, 200, 200))
            msg = f"[{sev.upper()}] {alert.get('message', '')}"
            if len(msg) > 80:
                msg = msg[:77] + "..."
            y = y_start + 18 + i * 22
            cv2.putText(display, msg, (15, y), self._font_small, 1.0, color, 1)

    def _draw_branding(self, display: np.ndarray):
        cv2.putText(display, "OmniSight Smart City Analytics", (10, 25), self._font, 0.6, (0, 200, 255), 2)

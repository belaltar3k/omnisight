from dataclasses import dataclass


@dataclass
class Config:
    # -- YOLO Detection --------------------------------------------------------
    yolo_model:          str   = "yolov8s.pt"
    yolo_conf:           float = 0.8
    yolo_classes:        tuple = (0,)  # person class only

    # -- ByteTrack Configuration -----------------------------------------------
    tracker_type:        str   = "bytetrack"
    track_high_thresh:   float = 0.5
    track_low_thresh:    float = 0.1
    new_track_thresh:    float = 0.6
    track_buffer:        int   = 60
    match_thresh:        float = 0.8
    fuse_score:          bool  = True

    # -- Feature Extraction ----------------------------------------------------
    face_model_name:     str   = "buffalo_l"
    face_det_size:       tuple = (160, 160)
    reid_model_name:     str   = "osnet_x1_0"
    reid_input_size:     tuple = (128, 256)  # (width, height)

    # -- FAISS Matching Thresholds ---------------------------------------------
    face_dim:            int   = 512
    appearance_dim:      int   = 512
    face_threshold:      float = 0.40
    appearance_threshold: float = 0.55
    max_appearance_vectors: int = 5
    appearance_search_k: int   = 5

    # -- Anti-Furniture Filters ------------------------------------------------
    min_crop_area:       int   = 4000
    min_aspect_ratio:    float = 1.4
    min_luminance_variance: float = 180.0
    min_color_variance:  float = 12.0
    n_confirm_frames:    int   = 4

    # -- Identity Fusion -------------------------------------------------------
    recheck_interval:    int   = 30

    # -- Box Deduplication -----------------------------------------------------
    iou_dedup_thresh:    float = 0.7

    # -- Database --------------------------------------------------------------
    db_path:             str   = "mtmct_identities.db"

    # -- Debug Flags -----------------------------------------------------------
    debug_scores:        bool  = True
    debug_show_rejections: bool = True

    # -- Misc ------------------------------------------------------------------
    device:              str   = "cuda"

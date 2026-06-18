# Hardware Specific bindings (NVDEC / CUDA)
class StreamDecoder:
    """
    Abstract decoder strategy separating generic CPU decoding (cv2 standard)
    from hardware-accelerated NVDEC pipelines.
    """
    def __init__(self, use_gpu=False):
        self.use_gpu = use_gpu

    def initialize_pipeline(self, url: str):
        if self.use_gpu:
            return self._init_nvdec(url)
        return self._init_cpu(url)

    def _init_nvdec(self, url: str):
        # Implementation for PyNvCodec or highly optimized GStreamer piplines
        pass
        
    def _init_cpu(self, url: str):
        pass

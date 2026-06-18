import time
import sys

def test_import(module_name):
    print(f"Importing {module_name}...", end="", flush=True)
    t0 = time.time()
    try:
        __import__(module_name)
        elapsed = time.time() - t0
        print(f" SUCCESS (took {elapsed:.2f}s)")
    except Exception as e:
        print(f" FAILED: {e}")

print("=== Testing Library Import Times ===")
test_import("numpy")
test_import("cv2")
test_import("torch")

# If torch succeeded, check CUDA initialization time
if "torch" in sys.modules:
    import torch
    print("Initializing PyTorch CUDA device...", end="", flush=True)
    t0 = time.time()
    try:
        is_avail = torch.cuda.is_available()
        elapsed = time.time() - t0
        print(f" Done (took {elapsed:.2f}s)")
        print(f"  CUDA available: {is_avail}")
        if is_avail:
            print(f"  Device Name: {torch.cuda.get_device_name(0)}")
            print("  Warm-up CUDA tensor creation...", end="", flush=True)
            t0 = time.time()
            try:
                x = torch.zeros(1, device="cuda")
                elapsed = time.time() - t0
                print(f" Done (took {elapsed:.2f}s)")
            except Exception as e:
                print(f" FAILED: {e}")
    except Exception as e:
        print(f" FAILED: {e}")

test_import("decord")
test_import("transformers")
test_import("ultralytics")
print("====================================")

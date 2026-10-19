"""
CutPilot Phase 2.2 — Experiment A: Qwen3-VL Instruct Software Optimization Benchmark

Measures performance of `qwen3-vl:4b-instruct-q4_K_M` vs baseline `qwen3-vl:4b`.
Runs the exact 2-frame test used in the warm benchmark:
- frame_offset_0.5s.jpg
- frame_offset_2.5s.jpg
Uses a concise prompt requiring JSON and limits response to ~150 tokens.
Runs 1 separate warm-up ping, followed by 3 warm test iterations.
Monitors RAM and CPU usage natively via Windows APIs.
"""

import os
import sys
import time
import json
import base64
import ctypes
import threading
import urllib.request
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
TEST_RESULTS_DIR = BASE_DIR / "test-results"
FRAMES_DIR = OUTPUTS_DIR / "clips" / "frames_3s"

FRAME1_PATH = FRAMES_DIR / "frame_offset_0.5s.jpg"
FRAME2_PATH = FRAMES_DIR / "frame_offset_2.5s.jpg"

OLLAMA_API_GENERATE = "http://127.0.0.1:11434/api/generate"
OLLAMA_API_TAGS = "http://127.0.0.1:11434/api/tags"

MODEL_NAME = "qwen3-vl:4b-instruct-q4_K_M"

# Windows Native Memory and CPU Monitoring
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength', ctypes.c_ulong),
        ('dwMemoryLoad', ctypes.c_ulong),
        ('ullTotalPhys', ctypes.c_ulonglong),
        ('ullAvailPhys', ctypes.c_ulonglong),
        ('ullTotalPageFile', ctypes.c_ulonglong),
        ('ullAvailPageFile', ctypes.c_ulonglong),
        ('ullTotalVirtual', ctypes.c_ulonglong),
        ('ullAvailVirtual', ctypes.c_ulonglong),
        ('sullAvailExtendedVirtual', ctypes.c_ulonglong)
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [('dwLowDateTime', ctypes.c_uint), ('dwHighDateTime', ctypes.c_uint)]


def get_ram_usage():
    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    total_gb = mem.ullTotalPhys / (1024 ** 3)
    used_gb = (mem.ullTotalPhys - mem.ullAvailPhys) / (1024 ** 3)
    avail_gb = mem.ullAvailPhys / (1024 ** 3)
    return {
        "total_gb": round(total_gb, 2),
        "used_gb": round(used_gb, 2),
        "avail_gb": round(avail_gb, 2),
        "percent_used": mem.dwMemoryLoad
    }


class CPUMonitor:
    def __init__(self, interval_s=1.0):
        self.interval_s = interval_s
        self.samples = []
        self._stop = threading.Event()
        self._thread = None

    def _filetime_to_int(self, ft):
        return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

    def _monitor(self):
        idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
        idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1))
        
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2))
            i = self._filetime_to_int(idle2) - self._filetime_to_int(idle1)
            k = self._filetime_to_int(kernel2) - self._filetime_to_int(kernel1)
            u = self._filetime_to_int(user2) - self._filetime_to_int(user1)
            total = k + u
            if total > 0:
                cpu_pct = round(((total - i) / total) * 100.0, 1)
                self.samples.append(cpu_pct)
            idle1, kernel1, user1 = idle2, kernel2, user2

    def start(self):
        self.samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        return {
            "avg_cpu_percent": round(statistics.mean(self.samples), 1) if self.samples else 0.0,
            "max_cpu_percent": max(self.samples) if self.samples else 0.0,
            "min_cpu_percent": min(self.samples) if self.samples else 0.0,
            "samples_count": len(self.samples)
        }


def check_model_installed(model_name: str) -> bool:
    try:
        req = urllib.request.Request(OLLAMA_API_TAGS)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            return model_name in models or f"{model_name}:latest" in models
    except Exception as e:
        print(f"Error connecting to Ollama tags endpoint: {e}")
        return False


def call_ollama(model: str, prompt: str, images_b64=None, options=None, keep_alive="60m"):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive
    }
    if images_b64:
        payload["images"] = images_b64
    if options:
        payload["options"] = options
    payload["format"] = "json"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_API_GENERATE, data=data, headers={"Content-Type": "application/json"})
    
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
    elapsed = time.perf_counter() - t0
    
    return res_json, elapsed


def main():
    print("=== CutPilot Phase 2.2 — Experiment A: Qwen3-VL Instruct Benchmark ===")
    
    # 1. Verify model availability
    print(f"Checking model '{MODEL_NAME}' in Ollama...")
    if not check_model_installed(MODEL_NAME):
        print(f"ERROR: Model '{MODEL_NAME}' is not found in Ollama local list.")
        print("Please ensure the model pull completes successfully before running this benchmark.")
        sys.exit(1)
    print(f"Confirmed: '{MODEL_NAME}' is installed.")
    
    # 2. Check input frames
    if not FRAME1_PATH.exists() or not FRAME2_PATH.exists():
        print(f"ERROR: Frame files not found: {FRAME1_PATH} or {FRAME2_PATH}")
        sys.exit(1)
        
    with open(FRAME1_PATH, "rb") as f:
        img1_b64 = base64.b64encode(f.read()).decode("utf-8")
    with open(FRAME2_PATH, "rb") as f:
        img2_b64 = base64.b64encode(f.read()).decode("utf-8")
    images_payload = [img1_b64, img2_b64]
    print(f"Loaded 2 test frames: {FRAME1_PATH.name} and {FRAME2_PATH.name}")
    
    # 3. Warm-up Request (Excluded from benchmark measurements)
    print("\n--- Step 1: Model Initialization & Separate Warm-Up ---")
    ram_before_warmup = get_ram_usage()
    print(f"Initial RAM: {ram_before_warmup['used_gb']} GB used / {ram_before_warmup['total_gb']} GB total ({ram_before_warmup['avail_gb']} GB free)")
    
    warmup_prompt = '{"action": "warmup", "instruction": "Respond strictly with valid JSON: {\\"status\\": \\"OK\\"}"}'
    warmup_res, warmup_elapsed = call_ollama(
        model=MODEL_NAME,
        prompt=warmup_prompt,
        options={"num_predict": 20, "temperature": 0.0},
        keep_alive="60m"
    )
    ram_after_warmup = get_ram_usage()
    print(f"Warm-up completed in {warmup_elapsed:.2f}s.")
    print(f"Warm-up metrics: load_duration={warmup_res.get('load_duration', 0)/1e6:.1f}ms, prompt_eval={warmup_res.get('prompt_eval_duration', 0)/1e6:.1f}ms, eval_count={warmup_res.get('eval_count', 0)}")
    print(f"RAM after model load: {ram_after_warmup['used_gb']} GB used ({ram_after_warmup['avail_gb']} GB free) -> Model weight memory: +{ram_after_warmup['used_gb'] - ram_before_warmup['used_gb']:.2f} GB")
    
    # 4. Define Concise Benchmark Prompt & Token Constraints
    prompt = (
        "Analyze these 2 frames from a 3-second video clip (from 00:03.0 to 00:06.0 of the screen recording). "
        "Output valid JSON only with keys: visible_elements, state_changes, readable_text, timestamps, uncertainty. "
        "Keep observations strictly factual, concise, and direct."
    )
    options = {
        "num_predict": 150,
        "temperature": 0.1
    }
    
    print("\n--- Step 2: Three Warm Benchmark Runs ---")
    print(f"Prompt: {prompt}")
    print(f"Constraint: num_predict = 150 tokens, format = json")
    
    runs = []
    
    for i in range(1, 4):
        print(f"\n>>> Running Warm Test #{i} of 3...")
        ram_start = get_ram_usage()
        cpu_mon = CPUMonitor(interval_s=1.0)
        cpu_mon.start()
        
        res, elapsed = call_ollama(
            model=MODEL_NAME,
            prompt=prompt,
            images_b64=images_payload,
            options=options,
            keep_alive="60m"
        )
        
        cpu_stats = cpu_mon.stop()
        ram_end = get_ram_usage()
        
        load_ms = res.get("load_duration", 0) / 1e6
        prompt_eval_ms = res.get("prompt_eval_duration", 0) / 1e6
        prompt_eval_count = res.get("prompt_eval_count", 0)
        eval_ms = res.get("eval_duration", 0) / 1e6
        eval_count = res.get("eval_count", 0)
        output_text = res.get("response", "").strip()
        
        # Validate output JSON
        is_json = False
        parsed_json = None
        has_required_keys = False
        try:
            parsed_json = json.loads(output_text)
            is_json = True
            req_keys = {"visible_elements", "state_changes", "readable_text", "timestamps", "uncertainty"}
            has_required_keys = req_keys.issubset(parsed_json.keys())
        except Exception:
            pass
            
        run_data = {
            "run_index": i,
            "total_elapsed_s": round(elapsed, 2),
            "load_duration_ms": round(load_ms, 2),
            "prompt_eval_tokens": prompt_eval_count,
            "prompt_eval_duration_s": round(prompt_eval_ms / 1000.0, 2),
            "vision_eval_tokens_per_sec": round(prompt_eval_count / (prompt_eval_ms / 1000.0), 2) if prompt_eval_ms > 0 else 0,
            "eval_tokens": eval_count,
            "eval_duration_s": round(eval_ms / 1000.0, 2),
            "generation_tokens_per_sec": round(eval_count / (eval_ms / 1000.0), 2) if eval_ms > 0 else 0,
            "ram_used_gb": ram_end["used_gb"],
            "ram_free_gb": ram_end["avail_gb"],
            "cpu_stats": cpu_stats,
            "output_is_valid_json": is_json,
            "output_has_required_keys": has_required_keys,
            "raw_output": output_text,
            "parsed_output": parsed_json
        }
        
        print(f"Run #{i} Completed in {elapsed:.2f}s:")
        print(f"  * Prompt/Vision Eval: {run_data['prompt_eval_duration_s']}s ({prompt_eval_count} tokens @ {run_data['vision_eval_tokens_per_sec']} t/s)")
        print(f"  * Autoregressive Gen: {run_data['eval_duration_s']}s ({eval_count} tokens @ {run_data['generation_tokens_per_sec']} t/s)")
        print(f"  * Model Load: {load_ms:.2f}ms (excluded/warm)")
        print(f"  * Avg CPU: {cpu_stats['avg_cpu_percent']}% (Peak: {cpu_stats['max_cpu_percent']}%)")
        print(f"  * RAM: {ram_end['used_gb']} GB used")
        print(f"  * JSON Schema Valid: {is_json} (Keys match: {has_required_keys})")
        
        runs.append(run_data)
        
    # 5. Compute Statistics & Medians
    total_times = [r["total_elapsed_s"] for r in runs]
    prompt_times = [r["prompt_eval_duration_s"] for r in runs]
    eval_times = [r["eval_duration_s"] for r in runs]
    eval_tokens = [r["eval_tokens"] for r in runs]
    cpu_avgs = [r["cpu_stats"]["avg_cpu_percent"] for r in runs]
    
    median_total = statistics.median(total_times)
    median_prompt = statistics.median(prompt_times)
    median_eval = statistics.median(eval_times)
    median_tokens = statistics.median(eval_tokens)
    median_cpu = statistics.median(cpu_avgs)
    
    # Baseline comparison (Phase 2 Warm Benchmark with qwen3-vl:4b)
    # Baseline: total=302.68s, prompt_eval=148.10s, eval=154.46s, tokens=1249
    baseline = {
        "model": "qwen3-vl:4b",
        "total_elapsed_s": 302.68,
        "prompt_eval_duration_s": 148.10,
        "eval_duration_s": 154.46,
        "eval_tokens": 1249
    }
    
    speedup_total = round(baseline["total_elapsed_s"] / median_total, 2) if median_total > 0 else 0
    gen_speedup = round(baseline["eval_duration_s"] / median_eval, 2) if median_eval > 0 else 0
    token_reduction_pct = round((1.0 - (median_tokens / baseline["eval_tokens"])) * 100.0, 1)
    
    summary = {
        "experiment": "Experiment A: Qwen3-VL Instruct Software Optimization Benchmark",
        "date": "2026-10-19",
        "model_tested": MODEL_NAME,
        "baseline_model": baseline["model"],
        "hardware": {
            "platform": "Qualcomm Snapdragon X2 Plus (X2P42100) ARM64 Windows 11",
            "cpu_cores": 6,
            "total_ram_gb": ram_after_warmup["total_gb"]
        },
        "warmup": {
            "warmup_duration_s": round(warmup_elapsed, 2),
            "cold_load_duration_ms": round(warmup_res.get("load_duration", 0)/1e6, 2),
            "ram_increase_gb": round(ram_after_warmup["used_gb"] - ram_before_warmup["used_gb"], 2)
        },
        "test_runs": runs,
        "medians": {
            "median_total_elapsed_s": median_total,
            "median_prompt_eval_duration_s": median_prompt,
            "median_generation_duration_s": median_eval,
            "median_generated_tokens": median_tokens,
            "median_cpu_percent": median_cpu,
            "variability_total_s": round(max(total_times) - min(total_times), 2)
        },
        "comparison_vs_baseline": {
            "baseline_total_s": baseline["total_elapsed_s"],
            "instruct_median_total_s": median_total,
            "total_speedup_factor": speedup_total,
            "baseline_generation_s": baseline["eval_duration_s"],
            "instruct_median_generation_s": median_eval,
            "generation_speedup_factor": gen_speedup,
            "token_reduction_percent": token_reduction_pct,
            "vision_encoder_change_s": round(median_prompt - baseline["prompt_eval_duration_s"], 2)
        }
    }
    
    out_path = TEST_RESULTS_DIR / "instruct_model_benchmark.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved structured benchmark results to {out_path}")
    print(f"Overall Result: Median Total Time = {median_total:.2f}s vs Baseline {baseline['total_elapsed_s']:.2f}s ({speedup_total}x speedup)")


if __name__ == "__main__":
    main()

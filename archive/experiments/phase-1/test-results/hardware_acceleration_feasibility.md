# CutPilot Phase 2.1 — Hardware Acceleration Feasibility Report

**Evaluation Date**: 2026-10-19  
**Target Video**: `phase-1/assets/test-15s.mp4`  
**Target Model**: `qwen3-vl:4b` (Q4_K_M GGUF, 3.14 GB, `sha256-9c60bdd691c1...`)  
**Host Architecture**: Qualcomm Snapdragon(R) X2 Plus - X2P42100 (6 Oryon CPU cores, 16 GB RAM, ARM64 Windows 11 Build 10.0.28000)  
**Accelerators Investigated**: Qualcomm Adreno(TM) X2-45 GPU, Qualcomm Hexagon(TM) NPU  

---

## 1. Executive Summary & Feasibility Status

| Acceleration Route | Target Accelerator | Runtime Architecture | Technical Status | Feasibility Determination |
| :--- | :--- | :--- | :--- | :--- |
| **Route 1: Native llama.cpp OpenCL** | Qualcomm Adreno X2-45 GPU | `ggml-opencl.dll` / OpenCL 3.0 | Hardware detected; Model load failed (`mRoPE` key); Vision encoder not offloaded | **UNSUPPORTED / INFEASIBLE** for Qwen3-VL |
| **Route 2: Native llama.cpp Hexagon HTP** | Qualcomm Hexagon NPU (45 TOPS) | `ggml-qnn.dll` / Qualcomm FastRPC | Hardware detected; Requires disabling Secure Boot & enabling Windows Test-Signing | **BLOCKED BY SECURITY POLICY** |
| **Route 3: Qualcomm QNN / ONNX Runtime** | Hexagon NPU / Adreno DirectML | QNN Execution Provider / ONNX | GGUF format unsupported; PyTorch & QNN SDK lack native Windows ARM64 PyPI wheels | **BLOCKED BY MODEL & TOOLCHAIN** |

> **Conclusion**: Hardware acceleration of the existing local `qwen3-vl:4b` video-understanding workflow using the Adreno GPU or Hexagon NPU is **not currently feasible** on this Windows ARM64 device without violating strict system security policies (Secure Boot / Test-Signing) or requiring extensive unsupported model re-architecture. The production pipeline must remain on CPU execution for now.

---

## 2. Hardware and Runtime Audit (Step 1)

A systematic low-level inspection of the system's drivers, APIs, and accelerator interfaces was conducted:

### 2.1 Qualcomm Adreno X2-45 GPU
- **Device**: `Qualcomm(R) Adreno(TM) X2-45 GPU` (Driver Version: `32.0.152.6`, Provider: Qualcomm).
- **Direct3D Feature Level**: D3D12 Feature Level `12_1` supported.
- **OpenCL Runtime**:
  - OpenCL ICD present at `C:\Windows\System32\OpenCL.dll` (535 KB).
  - OpenCL Platform 0 enumerated: `QUALCOMM Snapdragon(TM)`, Version: `QUALCOMM`.
  - OpenCL Device 0: `Qualcomm(R) Adreno(TM) X2-45 GPU` (OpenCL 3.0 QUALCOMM build `868.0 Compiler DX.50.42.00`).
  - Hardware Capabilities Verified:
    - `cl_khr_fp16`: **Supported** (Native FP16 floating-point arithmetic).
    - `cl_qcom_dot_product8`: **Supported** (8-bit integer dot-product tensor acceleration).
    - `cl_khr_subgroups`: **Supported**.
    - Global Memory: **7.81 GB** shared unified memory partition.
    - Max Work Group Size: **1,024**.

### 2.2 Qualcomm Hexagon NPU
- **Device**: `Snapdragon(R) X2 Plus - X2P42100 - Qualcomm(R) Hexagon(TM) NPU` (`ACPI\VEN_QCOM&DEV_0FF0`).
- **Class**: `ComputeAccelerator`, Status: `OK`.
- **Driver**: Version `30.0.220.11010` (Date: 27-01-2026, Provider: Qualcomm Technologies, Inc.).
- **Kernel Bridge**: `Qualcomm(R) FastRPC Device` (`ACPI\QCOM0F5C`) and `qcadsprpc8480.inf_arm64`.
- **Hardware Capability**: 45 TOPS INT8 / FP16 neural tensor engine.

### 2.3 Existing Ollama Runtime Audit
- Inspected the active Ollama installation directory (`C:\Users\yoges\AppData\Local\Programs\Ollama\lib\ollama`).
- **Critical Finding**: Ollama's Windows ARM64 binary distribution ships **strictly with `ggml-cpu.dll`**.
- It provides **zero GPU or NPU dynamic libraries** (`no ggml-opencl.dll`, `no ggml-vulkan.dll`, `no ggml-qnn.dll`).
- Ollama for Windows on Snapdragon is hardcoded to run 100% of tensor operations on the Oryon CPU.

---

## 3. Evaluation of Acceleration Routes (Step 2 & Step 3)

### Route 1: Native `llama.cpp` Adreno OpenCL Backend

To test this route safely without affecting Ollama, an isolated experimental environment was established in `phase-1/experimental/llama_opencl_adreno/` using the official native ARM64 release (`llama-b11724-bin-win-opencl-adreno-arm64.zip`):

1. **Backend Initialization**:
   Executing `llama-bench.exe` and `llama-cli.exe` confirmed that the native OpenCL backend loads and initializes the Adreno GPU:
   ```
   load_backend: loaded RPC backend from ... ggml-rpc.dll
   ggml_opencl: selected platform: 'QUALCOMM Snapdragon(TM)'
   ggml_opencl: device: 'Qualcomm(R) Adreno(TM) X2-45 GPU (OpenCL 3.0 Qualcomm(R) Adreno(TM) X2-45 GPU)'
   load_backend: loaded OpenCL backend from ... ggml-opencl.dll
   load_backend: loaded CPU backend from ... ggml-cpu.dll
   ```
2. **Model Ingestion Failure**:
   When pointing `llama-cli.exe` at the production GGUF blob (`sha256-9c60bdd691c18...`), model loading aborted immediately with:
   ```
   llama_model_load: error loading model: error loading model hyperparameters: key not found in model: qwen3vl.rope.dimension_sections
   llama_model_load_from_file_impl: failed to load model
   ```
   - **Root Cause**: Qwen3-VL utilizes Multimodal Rotary Position Embedding (M-RoPE) with partitioned spatial/temporal frequency slices (`[24, 20, 20, 0]`). Upstream `llama.cpp` treats `qwen3vl.rope.dimension_sections` as a mandatory hyperparameter. The Ollama GGUF checkpoint omits this key, relying on an internal fallback in Ollama's custom fork.
3. **Multimodal Operator Limitation in OpenCL**:
   - In `llama.cpp`, the `ggml-opencl` backend accelerates standard dense GEMM/matrix multiplications for language transformer layers.
   - The multimodal vision encoder (2D patch extraction, dynamic vision tokens, and visual cross-attention in `mtmd.dll`) **does not have OpenCL kernel implementations**.
   - Even if the language layers were offloaded, the **~72.5-second vision encoding bottleneck** would remain entirely on the CPU.

---

### Route 2: Native `llama.cpp` Hexagon HTP / NPU Backend (`ggml-qnn`)

1. **Hardware State**: The Hexagon NPU is operational in Windows Device Manager.
2. **Security & Driver-Signing Blockers**:
   - To offload computation to the Hexagon DSP via Qualcomm FastRPC on Windows on Snapdragon, the user-space DSP shared object (`libggml-htp-v*.so`) must be cryptographically signed by an authorized OEM/Qualcomm key.
   - For non-OEM or third-party builds, Qualcomm's documentation mandates:
     - **Disabling Secure Boot** in UEFI firmware.
     - **Enabling Windows Test-Signing Mode** (`bcdedit /set testsigning on`).
     - Installing unsigned driver development certificates.
   - **Compliance with Step 3**:
     The project instructions explicitly state:
     - *"Do not disable Secure Boot."*
     - *"Do not enable Windows test-signing mode."*
     - *"Do not install unsigned or untrusted kernel drivers."*
     - *"The native Hexagon backend may have additional driver-signing requirements. Investigate these first and stop if they would require the restricted changes above."*
   - **Result**: Route 2 is strictly **BLOCKED** by system security and driver-signing requirements.

---

### Route 3: Qualcomm QNN SDK / ONNX Runtime

1. **GGUF Model Format Incompatibility**:
   - Qualcomm QNN (Qualcomm AI Engine Direct) and the ONNX Runtime QNN Execution Provider cannot ingest GGUF models.
   - They require pre-compiled Qualcomm Context Binary caches (`.bin` / DLC format).
2. **Missing Toolchain & Python ARM64 Wheel Limitations**:
   - Compiling a model for QNN requires the Qualcomm AI Hub SDK (`qai-hub-models`) and PyTorch.
   - PyTorch (`torch`) and `onnxruntime-directml` **do not have precompiled native Windows ARM64 wheels on PyPI**.
3. **Dynamic Shape & M-RoPE Architectural Limitations**:
   - QNN Hexagon NPU execution graphs require strictly static tensor shapes.
   - Qwen3-VL uses dynamic visual token resolution based on image aspect ratio and Interleaved-MRoPE positional embeddings, which are not currently supported by Qualcomm's static NPU graph compiler.

---

## 4. CPU Baseline vs. Acceleration Comparison

| Metric | CPU Baseline (Measured in Phase 2) | Adreno GPU OpenCL (`ggml-opencl`) | Hexagon NPU (`ggml-qnn` / QNN) |
| :--- | :--- | :--- | :--- |
| **Model Load Status** | Success (Ollama `llama-server`) | **Failed** (`rope.dimension_sections` missing) | **Blocked** (FastRPC signing required) |
| **Vision Encoding Time** | **72.47s / image** (CPU Oryon) | 72.5s (Falls back to CPU; no OpenCL kernel) | N/A (Cannot initialize) |
| **Autoregressive Gen Time** | **154.46s** (8-10 tok/s on CPU) | N/A (Model load failure) | N/A (Cannot initialize) |
| **Total 3s Clip (2 Frames)** | **302.68s** (5.04 min) | Infeasible | Infeasible |
| **Accelerator Utilization** | 0% GPU / 0% NPU | 0% (Hardware verified; pipeline unlinked) | 0% (Hardware verified; driver blocked) |
| **System Security Impact** | None (Fully compliant) | None (Isolated in `phase-1/experimental/`) | **Violates Policy** (Requires Test-Signing) |

---

## 5. Practical Conclusions & Deployment Assessment

1. **Is Hardware Acceleration Feasible Today?**  
   **No.** On this Windows ARM64 machine, neither the Adreno X2-45 GPU nor the Hexagon NPU can be used to accelerate the existing `qwen3-vl:4b` video-understanding workflow without violating security policies or changing the model format.
2. **Is Under 3 Seconds per Frame Achievable on CPU?**  
   **No.** The vision encoder alone takes ~72.5 seconds per frame across 6 physical Oryon CPU cores.
3. **Should the Production Pipeline Be Modified?**  
   **No.** The existing CPU-based Ollama pipeline remains the only stable, working runtime on this machine.

---

## 6. Recommended Next Experiments (Practical Optimization Paths)

Because hardware accelerator offloading is currently blocked, latency reduction must be pursued through software-level architectural optimizations:

1. **Experiment A: Thinking Token Suppression (`/no_think`)**:
   - *Observation*: Out of the 286s single-frame request time, **~154 seconds** was consumed generating ~1,500 internal `<think> ... </think>` reasoning tokens.
   - *Test*: Evaluate passing reasoning constraints (`reasoning_effort: "low"` or prompt directives to suppress chain-of-thought) in Ollama.
   - *Potential Impact*: Reduces total generation time from ~154s to **~20-30s** without any hardware changes.
2. **Experiment B: Adaptive Shot-Boundary Keyframe Decimation**:
   - *Observation*: Fixed 1 fps or uniform sampling analyzes redundant frames within static scenes (e.g. 3 frames during a 5s quick-settings pull-down).
   - *Test*: Implement an ffmpeg scene detector (`gt(scene, 0.3)`) to extract frames *only* when an actual screen transition occurs.
   - *Potential Impact*: Reduces 15-second video analysis from 10 frames to 3 anchor frames, cutting total processing time by 70%.
3. **Experiment C: Monitoring Upstream Windows Copilot+ PC DirectML Releases**:
   - As Qualcomm and Microsoft release signed DirectML/NPU models for Windows on Snapdragon through the Windows App SDK, re-evaluate official signed ONNX packages that run without requiring test-signing mode.

---

## 7. Artifacts Preserved

All deliverables and prior test results in `phase-1/` remain intact:
- [`phase-1/test-results/warm_video_benchmark.md`](file:///C:/Users/yoges/Desktop/Projects/CutPilot/phase-1/test-results/warm_video_benchmark.md)
- [`phase-1/test-results/agent1_transcript.json`](file:///C:/Users/yoges/Desktop/Projects/CutPilot/phase-1/test-results/agent1_transcript.json)
- [`phase-1/test-results/agent1_transcript.txt`](file:///C:/Users/yoges/Desktop/Projects/CutPilot/phase-1/test-results/agent1_transcript.txt)
- [`phase-1/test-results/agent2_video_analysis.json`](file:///C:/Users/yoges/Desktop/Projects/CutPilot/phase-1/test-results/agent2_video_analysis.json)
- [`phase-1/test-results/agent2_video_analysis.md`](file:///C:/Users/yoges/Desktop/Projects/CutPilot/phase-1/test-results/agent2_video_analysis.md)
- [`phase-1/test-results/validation_report.md`](file:///C:/Users/yoges/Desktop/Projects/CutPilot/phase-1/test-results/validation_report.md)
- Experimental sandbox isolated in: `phase-1/experimental/llama_opencl_adreno/`

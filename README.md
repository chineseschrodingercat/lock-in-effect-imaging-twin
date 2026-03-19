# 🔬 FluoroLock: Digital Twin Simulator for Fluorescent Nanodiamond Assays
**Version:** 2.0.0 (Parallel Architecture)

FluoroLock is a highly modular, multithreaded digital twin physics engine and algorithmic evaluator for widefield Fluorescence Nanodiamond (FND) imaging. It is specifically designed to simulate and optimize point-of-care (POCT) optical setups, such as Raspberry Pi-based microscopes, for Digital Western Blots and Lateral Flow Assays (LFA).

This pipeline physically simulates background autofluorescence, thermal lensing, thermodynamic stage drift, laser photobleaching, and camera CMOS noise. It then benchmarks four distinct image processing algorithms—including our robust **Digital Lock-In Amplifier**—to determine the optimal limit of detection (LOD) across various microwave integration cycles and camera exposure times.

---

## 📊 Performance & Showdown Visualizations

The pipeline automatically generates publication-ready comparative analyses. Below are examples of the optimal configuration search and the 4PL standard curve fitting.

![4-Method Heatmap Showdown](data/100nm_run1/analysis_output/4_Method_Heatmap_Showdown.png)
*Figure 1: Algorithm Stability Landscape. Shows the thermal and mathematical failure points of traditional methods versus the Lock-In Amplifier across different hardware exposure and cycle times.*

![Optimal 4PL Curves](data/100nm_run1/analysis_output/4_Method_Optimal_4PL_Curves.png)
*Figure 2: Optimal 4PL Fitting Curves. Demonstrates the mathematical Limits of Detection (LOD) achieved by each algorithm at its individually optimized hardware setting.*

---

## 🚀 Architecture (v2.0)

The `v2` release introduces a unified, 5-file object-oriented architecture. **Everything is controlled and executed from `main.py`.**

* `main.py` - The Control Center. Run this to execute your sweeps and evaluations.
* `config.py` - The Physics Engine. Contains static thermodynamic, optical, and algorithm constants.
* `simulator.py` - The multithreaded generator that builds 12-bit TIFF stacks of physical FOVs.
* `evaluator.py` - The 4-method benchmarking engine that outputs 2x2 heatmaps and 4PL curves.
* `methods.py` - The isolated image processing math (Global Thresholding, Rolling Ball, Single-Frame, Lock-In).

---

## 💻 Usage & Quick Start

### 1. Installation
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/YourUsername/lock-in-effect-imaging-twin.git
cd lock-in-effect-imaging-twin
pip install -r requirements.txt
```

### 2. Execution
To run a full hardware sweep and algorithm evaluation, simply configure your experimental matrix in `main.py` and run:
```bash
python main.py
```

### 3. Output Directory Structure
Data is automatically routed into a unified auto-incrementing folder system to prevent overwriting.
```text
data/
└── 100nm_run1/
    ├── 0.25s/
    │   └── Rep_1/
    │       └── 50_FNDs/
    │           ├── ON/            # Raw 12-bit TIFFs (Microwave ON)
    │           ├── OFF/           # Raw 12-bit TIFFs (Microwave OFF)
    │           └── VISUAL_RED/    # Strictly-mapped 8-bit PNGs for presentation
    └── analysis_output/
        ├── fused_4method_results.csv
        ├── Heatmap_Standalone_Lock_In_Amplifier.png
        ├── 4_Method_Heatmap_Showdown.png
        └── 4_Method_Optimal_4PL_Curves.png
```

---

## 🎛️ PART 1: Routine Sweep Controls (`main.py`)

These are the frequently changed parameters that govern your experimental matrix. They dictate *what* you are testing and sweeping. Modify these directly inside `main.py`.

### Execution Routing
* **`EXECUTION_MODE`**: Controls the pipeline phase.
  * *Options:* `"simulate_only"`, `"evaluate_only"`, `"run_both"`
* **`TARGET_RUN_FOLDER`**: Tells the evaluator which data to analyze if you skipped simulation.
  * *Options:* `"latest"` (auto-grabs the newest run), or a specific string like `"100nm_run2"`.

### Hardware Matrix (The Sweep Space)
* **`EXPOSURE_CHECKPOINTS`**: The camera integration times to simulate.
  * *Suggested Range:* `[0.1, 0.25, 0.5, 1.0]` seconds. 
  * *Note:* Longer exposures dramatically increase simulated background thermal noise and dark current.
* **`CYCLE_CHECKPOINTS`**: The total number of Microwave ON/OFF modulations to extract signal from.
  * *Suggested Range:* `[1, 5, 10, 20, 50, 80, 100]`. 
  * *Note:* High cycles test the algorithm's resilience to continuous mechanical stage drift and laser photobleaching.

### Biological Sample Design
* **`TARGET_FND_COUNTS`**: The true ground-truth number of FNDs dropped into the simulated Field of View (FOV). Used to build the 4PL standard curve.
  * *Suggested Setup:* Include `0` (for blank LOD thresholding) and scale logarithmically, e.g., `[0, 5, 10, 50, 100, 500]`.
* **`NUM_REPLICATES`**: The number of statistically independent FOVs generated for *every* condition. 
  * *Suggested Range:* `3` (Standard error bars) to `5` (Rigorous publication).
* **`PARTICLE_MODE`**: Selects the physical FND size matrix.
  * *Options:* `"100nm"` or `"600nm"`.

### Computing Power
* **`MAX_PARALLEL_WORKERS`**: The number of simultaneous Python environments spawned across your CPU.
  * *Suggested Range:* **Your Total Logical Processors minus 2**. Do *not* exceed your total thread count, or context switching and RAM exhaustion will crash the pipeline. (e.g., for an 8-Core/16-Thread CPU, use `14`).
* **`SIZE_X` & `SIZE_Y`**: The resolution of the simulated CMOS sensor. 
  * *Suggested Range:* `960` x `720` (Typical for 2x2 Binning mode). Higher resolutions exponentially increase RAM usage during multiprocessing.

---

## ⚙️ PART 2: Advanced Physics & Algorithmic Settings (`config.py`)

These are the deep-engine variables. They define the physical realities of the biological sample, the optical train, and the mathematical thresholds for the algorithms. Modify these inside `config.py`.

### 1. Particle & Signal Physics
* **`ODMR_DROP`**: The quantum contrast ratio of the NV centers under microwave resonance.
  * *Suggested Range:* `0.01` (Dirty/Deep tissue) to `0.03` (Perfect surface resonance). Default: `0.02`.
* **`PHOTON_YIELD`**: Theoretical flux of photons emitted by a single FND per second reaching the sensor.
  * *Suggested Range:* `2000.0` for 100nm. `5000.0` for 600nm (Capped intentionally to prevent mathematically instant 12-bit sensor saturation).

### 2. Clinical Validation Filters
* **`MIN_SIGNAL_RISE`**: The multiplier over the blank background required to consider a curve valid.
  * *Suggested Range:* `1.2` (20% above noise) to `1.5`.
* **`MIN_R_SQUARED`**: The minimum coefficient of determination for the 4PL curve fit. If it falls below this, the LOD is rejected and rendered grey on the heatmap.
  * *Suggested Range:* `0.90` (Standard) to `0.95` (Strict clinical grade).

### 3. Algorithm Processing Thresholds
* **`ALG_MAD_MULTIPLIER`**: The strictness of the signal thresholding (x * Median Absolute Deviation).
  * *Suggested Range:* `3.0` to `5.0`. (Default: `4.0`).
* **`ALG_TOPHAT_DISK_SIZE`**: The structural element size for the Rolling Ball background subtraction. Must be larger than your FND Airy disk.
  * *Suggested Range:* `15` to `30` pixels.
* **`ALG_DOG_LOW_SIGMA` / `ALG_DOG_HIGH_SIGMA`**: The bandpass limits for the Difference of Gaussians (DoG) filter, used to strip thermal waves and high-frequency read noise.
  * *Suggested Range:* Low: `0.5 - 1.5`, High: `3.0 - 7.0`.
* **`ALG_ALIGN_UPSAMPLE`**: Sub-pixel resolution factor for cross-correlation mechanical drift correction.
  * *Suggested Range:* `10` (0.1 pixel accuracy) to `100` (0.01 pixel accuracy, extremely slow to compute).

### 4. Base Optics & Camera Noise
* **`CAMERA_SATURATION`**: The physical well depth limit of the simulated sensor.
  * *Value:* `4095.0` (for 12-bit uncompressed RAW CMOS).
* **`BACKGROUND_PHOTONS`**: The base autofluorescence of the nitrocellulose membrane/tissue.
  * *Suggested Range:* `1000.0` (Clean) to `3000.0` (Highly fluorescent/dirty sample).
* **`DARK_CURRENT_RATE`**: Thermal electrons accumulating per pixel per second.
  * *Suggested Range:* `5.0` (Cooled sensor) to `25.0` (Uncooled POCT sensor).
* **`EXCESS_SHOT_NOISE_MULTIPLIER`**: Amplifies the standard Poisson noise.
  * *Suggested Range:* `1.0` to `1.5`.

### 5. Thermodynamics & Fluid Dynamics
* **`ODMR_THERMAL_HALF_LIFE`**: Seconds of continuous microwave exposure before the thermal expansion destroys the resonance tracking.
  * *Suggested Range:* `5.0` to `20.0` seconds depending on your heatsink configuration.
* **`LASER_DIMMING_PER_SEC`**: Photobleaching rate of the background tissue (FNDs do not bleach).
  * *Suggested Range:* `0.01` (1% per second) to `0.05`.
* **`DRIFT_PX_PER_SEC`**: Mechanical XYZ stage drift caused by thermal expansion of the microscope chassis.
  * *Suggested Range:* `0.1` (Stable optical table) to `1.5` (Unstable 3D-printed chassis).
* **`THERMAL_LENSING_SHIFT`**: Artificial focus-shift factor induced by microwave heating of the fluid phase.
  * *Suggested Range:* `0.05` to `0.3`.
* **`BIO_GRAIN_CONTRAST` & `BACKGROUND_CLOUDINESS`**: Controls the "clumpiness" of the biological junk, explicitly designed to break Rolling Ball algorithms.
  * *Suggested Range:* Grain: `0.05 - 0.20`. Cloudiness: `0.2 - 0.6`.

### 6. Advanced Engine Tuning (Developers Only)
* **`PSF_SIGMA`**: The physical spread of the Point Spread Function (Airy Disk).
  * *Suggested Range:* `1.0` to `2.0` depending on your NA.
* **`AIRY_RING_MULTIPLIER`**: Artificially brightens the outer diffraction rings of the FND to challenge the alignment algorithms.
  * *Suggested Range:* `2.0` to `6.0`.
* **`ILLUM_CENTER_X_RATIO` & `ILLUM_SPREAD`**: Defines the Gaussian beam profile of the laser. `0.5` is perfectly centered. Off-centering simulates misaligned POCT hardware.

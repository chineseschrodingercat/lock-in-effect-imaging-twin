import os
import time
import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import shift
from skimage import filters
from skimage.registration import phase_cross_correlation
from skimage.morphology import white_tophat, disk
from scipy.optimize import curve_fit

import matplotlib
matplotlib.use('TkAgg') 
import matplotlib.pyplot as plt
import config  # 👈 Imports your master settings!

class BenchmarkEvaluator:
    def __init__(self):
        self.reference_img = None

    def _load_image(self, img_path):
        img_arr = np.array(Image.open(img_path))
        if img_arr.ndim == 3: return img_arr[:, :, 0].astype(float)
        return img_arr.astype(float)

    def extract_signals(self, conc_path):
        on_dir = os.path.join(conc_path, "ON")
        off_dir = os.path.join(conc_path, "OFF")
        on_files = sorted([os.path.join(on_dir, f) for f in os.listdir(on_dir)])
        off_files = sorted([os.path.join(off_dir, f) for f in os.listdir(off_dir)])
        num_cycles = min(len(on_files), len(off_files))
        
        if num_cycles == 0: return 0.0, 0.0, 0.0, 0.0
        img_raw = self._load_image(off_files[0])

        # --- ALGORITHM 1: Thresholding ---
        img_smooth = filters.gaussian(img_raw, sigma=1.0, preserve_range=True)
        med_1 = np.median(img_smooth)
        mad_1 = np.median(np.abs(img_smooth - med_1)) * 1.4826
        if mad_1 == 0: mad_1 = np.std(img_smooth)
        pixels_alg1 = img_smooth[img_smooth > med_1 + (5.0 * mad_1)]
        flux_alg1 = np.sum(pixels_alg1) if len(pixels_alg1) > 0 else 0.0

        # --- ALGORITHM 2: Rolling Ball ---
        img_rb = white_tophat(img_raw, footprint=disk(20))
        img_rb_smooth = filters.gaussian(img_rb, sigma=1.0, preserve_range=True)
        med_rb = np.median(img_rb_smooth)
        mad_rb = np.median(np.abs(img_rb_smooth - med_rb)) * 1.4826
        if mad_rb == 0: mad_rb = np.std(img_rb_smooth)
        pixels_alg2 = img_rb_smooth[img_rb_smooth > med_rb + (5.0 * mad_rb)]
        flux_alg2 = np.sum(pixels_alg2) if len(pixels_alg2) > 0 else 0.0

        # --- ALGORITHM 3: Single-Frame ---
        img_on_raw = self._load_image(on_files[0])
        shift_val, _, _ = phase_cross_correlation(img_raw, img_on_raw, upsample_factor=10)
        if np.max(np.abs(shift_val)) > 15.0: shift_val = [0.0, 0.0]
        img_on_aligned = shift(img_on_raw, shift=shift_val, mode='nearest')
        
        diff_smooth = filters.gaussian(img_raw - img_on_aligned, sigma=1.0, preserve_range=True)
        med_3 = np.median(diff_smooth)
        mad_3 = np.median(np.abs(diff_smooth - med_3)) * 1.4826
        if mad_3 == 0: mad_3 = np.std(diff_smooth)
        pixels_alg3 = diff_smooth[diff_smooth > med_3 + (5.0 * mad_3)]
        flux_alg3 = np.sum(pixels_alg3) if len(pixels_alg3) > 0 else 0.0

        # --- ALGORITHM 4: Lock-In Amplifier ---
        self.reference_img = img_raw
        off_sum_map = np.zeros_like(img_raw, dtype=float)
        on_sum_map = np.zeros_like(img_raw, dtype=float)
        
        for i in range(num_cycles):
            off_img = self._load_image(off_files[i])
            on_img = self._load_image(on_files[i])
            s, _, _ = phase_cross_correlation(self.reference_img, off_img, upsample_factor=10)
            if np.max(np.abs(s)) > 15.0: s = [0.0, 0.0]
            off_sum_map += shift(off_img, shift=s, mode='nearest')
            on_sum_map += shift(on_img, shift=s, mode='nearest')

        lockin_map = filters.gaussian((off_sum_map - on_sum_map) / num_cycles, sigma=1.0, preserve_range=True)
        med_4 = np.median(lockin_map)
        mad_4 = np.median(np.abs(lockin_map - med_4)) * 1.4826
        if mad_4 == 0: mad_4 = np.std(lockin_map)
        pixels_alg4 = lockin_map[lockin_map > med_4 + (5.0 * mad_4)]
        flux_alg4 = np.sum(pixels_alg4) if len(pixels_alg4) > 0 else 0.0

        return flux_alg1, flux_alg2, flux_alg3, flux_alg4

def four_pl_model(x, A, B, C, D):
    return D + (A - D) / (1.0 + (x / C)**B)

if __name__ == "__main__":
    if not os.path.exists(config.DATA_ROOT):
        print(f"❌ Error: Directory '{config.DATA_ROOT}' not found.")
        exit()
        
    sample_rep_dir = os.path.join(config.DATA_ROOT, "Rep_1")
    conc_map = {}
    for f in os.listdir(sample_rep_dir):
        if f.endswith("_FNDs"):
            try:
                conc_map[float(f.replace("_FNDs", ""))] = f
            except ValueError: pass
                
    sorted_concs = np.array(sorted(conc_map.keys()))
    evaluator = BenchmarkEvaluator()
    
    results = {
        'Alg1': {'x': [], 'y': [], 'yerr': [], 'blank': 0.0, 'sd': 0.0, 'lod_val': np.nan, 'name': 'Global Thresholding'},
        'Alg2': {'x': [], 'y': [], 'yerr': [], 'blank': 0.0, 'sd': 0.0, 'lod_val': np.nan, 'name': 'Rolling Ball'},
        'Alg3': {'x': [], 'y': [], 'yerr': [], 'blank': 0.0, 'sd': 0.0, 'lod_val': np.nan, 'name': 'Single-Frame'},
        'Alg4': {'x': [], 'y': [], 'yerr': [], 'blank': 0.0, 'sd': 0.0, 'lod_val': np.nan, 'name': 'Lock-In Amplifier'}
    }
    raw_data = {alg: {conc: [] for conc in sorted_concs} for alg in results.keys()}
    
    print(f"\n🚀 Running Benchmark Showdown ({config.NUM_REPLICATES} Replicates)...")
    start_time = time.time()
    
    for rep in range(1, config.NUM_REPLICATES + 1):
        print(f" -> Processing Replicate {rep}...")
        rep_dir = os.path.join(config.DATA_ROOT, f"Rep_{rep}")
        for conc in sorted_concs:
            f1, f2, f3, f4 = evaluator.extract_signals(os.path.join(rep_dir, conc_map[conc]))
            raw_data['Alg1'][conc].append(f1)
            raw_data['Alg2'][conc].append(f2)
            raw_data['Alg3'][conc].append(f3)
            raw_data['Alg4'][conc].append(f4)

    for alg in results.keys():
        for conc in sorted_concs:
            flux_arr = np.array(raw_data[alg][conc])
            mean_flux, std_flux = np.mean(flux_arr), np.std(flux_arr)
            if conc == 0.0:
                results[alg]['blank'] = mean_flux
                results[alg]['sd'] = max(std_flux, 1e-6) 
            results[alg]['x'].append(conc)
            results[alg]['y'].append(mean_flux)
            results[alg]['yerr'].append(std_flux)
            
    print(f"✅ Processing complete in {time.time() - start_time:.1f} seconds.\n")

    # --- PLOTTING & LOD CALCULATION ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.canvas.manager.set_window_title('Algorithm Benchmark Showdown')
    
    algorithms = [
        (0, 0, "1. Global Thresholding", results['Alg1'], '#d62728', 'Alg1'),
        (0, 1, "2. Rolling Ball Subtraction", results['Alg2'], '#9467bd', 'Alg2'),
        (1, 0, "3. Single-Frame Subtraction", results['Alg3'], '#ff7f0e', 'Alg3'),
        (1, 1, "4. Digital Lock-In Amplifier", results['Alg4'], '#2ca02c', 'Alg4')
    ]

    for row, col, name, data, color, alg_key in algorithms:
        ax = axes[row, col]
        x_data, y_data, y_err = np.array(data['x']), np.array(data['y']), np.array(data['yerr'])
        lod_y = data['blank'] + (3.0 * data['sd'])
        
        mask_nonzero = x_data > 0
        x_fit, y_fit = x_data[mask_nonzero], y_data[mask_nonzero]
        min_x = np.min(x_fit) if len(x_fit) > 0 else 1
        display_x = np.where(x_data == 0, min_x / 3.0, x_data)
        
        ax.errorbar(display_x, y_data, yerr=y_err, fmt='o', color=color, ecolor='black', elinewidth=1.5, capsize=4, zorder=5)
        ax.axhline(y=lod_y, color='gray', ls='--', label=f'LOD Threshold')
        
        signal_max = np.max(y_fit) if len(y_fit) > 0 else 0
        if signal_max >= (max(data['blank'], 1e-6) * config.MIN_SIGNAL_RISE) and signal_max > lod_y:
            try:
                guess = [np.min(y_fit), 1.0, np.median(x_fit), signal_max]
                popt, _ = curve_fit(four_pl_model, x_fit, y_fit, p0=guess, sigma=(y_err[mask_nonzero] + 1e-8), absolute_sigma=False, maxfev=5000)
                smooth_x = np.logspace(np.log10(min_x/3.0), np.log10(np.max(x_fit)*1.2), 100)
                ax.plot(smooth_x, four_pl_model(smooth_x, *popt), color=color, lw=2.5)
                
                A, B, C, D = popt
                if min(A, D) < lod_y < max(A, D):
                    lod_x = C * (((A - D) / (lod_y - D)) - 1.0)**(1.0 / B)
                    results[alg_key]['lod_val'] = lod_x # SAVE FOR CSV
                    ax.axvline(x=lod_x, color='purple', ls=':', lw=2, label=f'LOD: {lod_x:.1f} FNDs')
                    ax.plot(lod_x, lod_y, marker='*', color='gold', ms=14, mec='black', zorder=10)
            except: ax.plot(display_x, y_data, color=color, lw=1.5, alpha=0.5, ls=':')
        else:
            ax.plot(display_x, [np.mean(y_data)]*len(display_x), color=color, lw=2.5, ls='-', label=f'Flat Signal')
            
        ax.set_xscale('log')
        ax.set_title(name, fontsize=13, fontweight='bold')
        if row == 1: ax.set_xlabel("Number of True FNDs per FOV")
        if col == 0: ax.set_ylabel("Total Integrated Flux (a.u.)")
        ax.set_xticks([min_x / 3.0] + list(x_fit))
        ax.set_xticklabels(['0'] + [str(int(x)) for x in x_fit])
        ax.grid(True, which='major', alpha=0.6)
        ax.legend(loc='upper left', fontsize=9)

    plt.tight_layout()
    plt.savefig("Benchmark_Showdown_Quad_ErrorBars.png", dpi=300)
    
    # --- 💾 FUSE REPLICATES INTO CSV EXPORT ---
    csv_rows = []
    for alg_key, data in results.items():
        for i, conc in enumerate(data['x']):
            csv_rows.append({
                "Algorithm": data['name'],
                "True_FND_Count": conc,
                "Mean_Flux": data['y'][i],
                "Standard_Deviation": data['yerr'][i],
                "Final_Calculated_LOD": data['lod_val'] if conc == 0 else "" # Only list LOD once per algorithm
            })
            
    df = pd.DataFrame(csv_rows)
    csv_path = "data/fused_results.csv"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"💾 Fused numerical data successfully exported to: {csv_path}")
    
    plt.show()

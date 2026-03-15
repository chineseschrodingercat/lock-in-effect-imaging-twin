import os
import time
import numpy as np
from PIL import Image
from scipy.ndimage import shift, gaussian_filter
from scipy.signal import fftconvolve
from scipy.special import j1
import config  # 👈 Imports your master settings!

def generate_airy_psf(sigma, ring_boost, size=41):
    y, x = np.meshgrid(np.arange(size) - size//2, np.arange(size) - size//2)
    r = np.sqrt(x**2 + y**2)
    z = r * (3.8317 / (2.5 * sigma))
    z[size//2, size//2] = 1e-8 
    psf = (2 * j1(z) / z)**2
    ring_mask = z > 3.8317
    psf[ring_mask] = psf[ring_mask] * ring_boost 
    return psf / np.max(psf)

def run_digital_twin_simulator():
    print(f"🔴 Starting True Random Walk Simulation: {config.PARTICLE_MODE} FNDs")
    
    sigma_start = config.PSF_SIGMA
    sigma_end = sigma_start + config.Z_AXIS_FOCAL_DRIFT
    psf_start = generate_airy_psf(sigma=sigma_start, ring_boost=config.AIRY_RING_MULTIPLIER)
    psf_end = generate_airy_psf(sigma=sigma_end, ring_boost=config.AIRY_RING_MULTIPLIER)
    
    xx, yy = np.meshgrid(np.arange(config.SIZE_X), np.arange(config.SIZE_Y))
    b1_gradient_profile = 1.0 - (config.B1_MICROWAVE_GRADIENT * (xx / config.SIZE_X))
    odmr_map = config.ODMR_DROP * b1_gradient_profile

    center_x, center_y = config.SIZE_X * 0.45, config.SIZE_Y * 0.5 
    illum_profile = np.exp(-(((xx - center_x)**2) + ((yy - center_y)**2)) / (2 * (config.SIZE_X * 0.6)**2))
    illum_profile = illum_profile * config.VIGNETTING_STRENGTH + (1.0 - config.VIGNETTING_STRENGTH)

    raw_static_macro = np.random.normal(0, 1, (config.SIZE_Y, config.SIZE_X))
    smooth_clouds = gaussian_filter(raw_static_macro, sigma=45.0) 
    smooth_clouds = (smooth_clouds - np.min(smooth_clouds)) / (np.max(smooth_clouds) - np.min(smooth_clouds))
    cloud_multiplier = (smooth_clouds * config.BACKGROUND_CLOUDINESS * 2.0) + (1.0 - config.BACKGROUND_CLOUDINESS)

    raw_static_micro = np.random.normal(0, 1, (config.SIZE_Y, config.SIZE_X))
    bio_grain = gaussian_filter(raw_static_micro, sigma=config.BIO_GRAIN_SIZE)
    bio_grain = (bio_grain - np.mean(bio_grain)) / (np.std(bio_grain) + 1e-8)
    grain_multiplier = np.clip(1.0 + (bio_grain * config.BIO_GRAIN_CONTRAST), 0.1, 3.0)

    start_time = time.time()

    for rep in range(1, config.NUM_REPLICATES + 1):
        print(f"\n--- 🧪 RUNNING REPLICATE {rep} OF {config.NUM_REPLICATES} ---")
        
        for fnd_count in config.TARGET_FND_COUNTS:
            folder_name = f"{fnd_count}_FNDs"
            conc_dir = os.path.join(config.DATA_ROOT, f"Rep_{rep}", folder_name)
            on_dir, off_dir = os.path.join(conc_dir, "ON"), os.path.join(conc_dir, "OFF")
            os.makedirs(on_dir, exist_ok=True)
            os.makedirs(off_dir, exist_ok=True)
            
            debris_static = np.zeros((config.SIZE_Y, config.SIZE_X))
            debris_floating = np.zeros((config.SIZE_Y, config.SIZE_X))
            junk_locations = []

            def get_clustered_location(prob, loc_list):
                if len(loc_list) > 0 and np.random.rand() < prob:
                    base_cx, base_cy = loc_list[np.random.randint(0, len(loc_list))]
                    cx = np.clip(base_cx + np.random.randint(-4, 4), 20, config.SIZE_X - 20)
                    cy = np.clip(base_cy + np.random.randint(-4, 4), 20, config.SIZE_Y - 20)
                else:
                    cx, cy = np.random.randint(20, config.SIZE_X - 20), np.random.randint(20, config.SIZE_Y - 20)
                loc_list.append((cx, cy))
                return cx, cy

            for _ in range(config.ACTIVE_FND["JUNK_COUNT"]):
                cx, cy = get_clustered_location(config.JUNK_CLUSTERING_PROBABILITY, junk_locations)
                scale = np.random.exponential(scale=3.5) + 1.5 
                sigma_x, sigma_y = scale, scale * np.random.uniform(0.3, 3.0) 
                theta = np.random.uniform(0, np.pi) 
                amp = np.random.uniform(300.0, config.ACTIVE_FND["PHOTON_YIELD"] * 1.2) 
                
                a = np.cos(theta)**2/(2*sigma_x**2) + np.sin(theta)**2/(2*sigma_y**2)
                b = -np.sin(2*theta)/(4*sigma_x**2) + np.sin(2*theta)/(4*sigma_y**2)
                c = np.sin(theta)**2/(2*sigma_x**2) + np.cos(theta)**2/(2*sigma_y**2)
                
                box_size = int(max(sigma_x, sigma_y) * 4)
                y_min, y_max = max(0, cy - box_size), min(config.SIZE_Y, cy + box_size + 1)
                x_min, x_max = max(0, cx - box_size), min(config.SIZE_X, cx + box_size + 1)
                
                if y_max > y_min and x_max > x_min:
                    xx_box, yy_box = xx[y_min:y_max, x_min:x_max], yy[y_min:y_max, x_min:x_max]
                    envelope = np.exp(- (a*(xx_box - cx)**2 + 2*b*(xx_box - cx)*(yy_box - cy) + c*(yy_box - cy)**2))
                    raw_noise = np.random.rand(y_max - y_min, x_max - x_min)
                    texture = gaussian_filter(raw_noise, sigma=scale*0.4) 
                    texture = (texture - np.min(texture)) / (np.max(texture) - np.min(texture) + 1e-8)
                    blob = envelope * (texture * 0.9 + 0.1) * amp
                    
                    if np.random.rand() < config.FLOATING_DEBRIS_FRACTION:
                        debris_floating[y_min:y_max, x_min:x_max] += blob
                    else:
                        debris_static[y_min:y_max, x_min:x_max] += blob

            for _ in range(config.NUM_DEFOCUS_DONUTS):
                cx, cy = get_clustered_location(config.JUNK_CLUSTERING_PROBABILITY, junk_locations)
                scale = np.random.uniform(4.0, 10.0) 
                amp = np.random.uniform(300.0, config.ACTIVE_FND["PHOTON_YIELD"])
                box_size = int(scale * 4)
                y_min, y_max = max(0, cy - box_size), min(config.SIZE_Y, cy + box_size + 1)
                x_min, x_max = max(0, cx - box_size), min(config.SIZE_X, cx + box_size + 1)
                
                if y_max > y_min and x_max > x_min:
                    xx_box, yy_box = xx[y_min:y_max, x_min:x_max], yy[y_min:y_max, x_min:x_max]
                    r_squared = (xx_box - cx)**2 + (yy_box - cy)**2
                    donut = (r_squared / (2 * scale**2)) * np.exp(-r_squared / (2 * scale**2)) * amp
                    
                    if np.random.rand() < config.FLOATING_DEBRIS_FRACTION:
                        debris_floating[y_min:y_max, x_min:x_max] += donut
                    else:
                        debris_static[y_min:y_max, x_min:x_max] += donut

            for _ in range(config.NUM_SALT_PEPPER_DUST):
                cx, cy = get_clustered_location(config.JUNK_CLUSTERING_PROBABILITY, junk_locations)
                debris_static[cy, cx] += np.random.uniform(500.0, config.CAMERA_SATURATION * 0.8)

            fake_dots_static_raw = np.zeros((config.SIZE_Y, config.SIZE_X))
            fake_dots_floating_raw = np.zeros((config.SIZE_Y, config.SIZE_X))
            
            for _ in range(config.ACTIVE_FND["FAKE_FND_COUNT"]):
                cx, cy = get_clustered_location(config.JUNK_CLUSTERING_PROBABILITY, junk_locations)
                dimmer_amplitude = np.random.uniform(0.1, 0.4) 
                if np.random.rand() < config.FLOATING_DEBRIS_FRACTION:
                    fake_dots_floating_raw[cy, cx] += dimmer_amplitude
                else:
                    fake_dots_static_raw[cy, cx] += dimmer_amplitude
                    
            fake_dots_static_start = fftconvolve(fake_dots_static_raw, psf_start, mode='same')
            fake_dots_static_end = fftconvolve(fake_dots_static_raw, psf_end, mode='same')
            fake_dots_floating_start = fftconvolve(fake_dots_floating_raw, psf_start, mode='same')
            fake_dots_floating_end = fftconvolve(fake_dots_floating_raw, psf_end, mode='same')

            real_dots_raw = np.zeros((config.SIZE_Y, config.SIZE_X))
            target_locations = []
            
            if fnd_count > 0:
                for _ in range(fnd_count):
                    cx, cy = get_clustered_location(config.CLUSTERING_PROBABILITY, target_locations)
                    real_dots_raw[cy, cx] += 1.0
                real_dots_start = fftconvolve(real_dots_raw, psf_start, mode='same')
                real_dots_end = fftconvolve(real_dots_raw, psf_end, mode='same')
                print(f"   -> Processing FOV with {fnd_count} True FNDs...")
            else:
                real_dots_start, real_dots_end = real_dots_raw, real_dots_raw
                print(f"   -> Processing Blank Control (0 True FNDs)...")

            current_flow_x = 0.0
            current_flow_y = 0.0

            for i in range(config.CYCLES):
                time_frac = i / max(1, config.CYCLES - 1)
                
                laser_bleach = 1.0 - (config.LASER_DIMMING * time_frac)
                laser_flicker = np.random.normal(1.0, config.LASER_INSTABILITY)
                
                current_real_dots = (real_dots_start * (1.0 - time_frac)) + (real_dots_end * time_frac)
                current_fake_static = (fake_dots_static_start * (1.0 - time_frac)) + (fake_dots_static_end * time_frac)
                current_fake_floating_blurred = (fake_dots_floating_start * (1.0 - time_frac)) + (fake_dots_floating_end * time_frac)
                
                if i > 0:
                    current_flow_x += config.FLUID_FLOW_X + np.random.normal(0, config.BROWNIAN_WOBBLE_STD)
                    current_flow_y += config.FLUID_FLOW_Y + np.random.normal(0, config.BROWNIAN_WOBBLE_STD)
                
                current_floating_debris = shift(debris_floating, shift=[current_flow_y, current_flow_x], mode='nearest')
                current_fake_floating_shifted = shift(current_fake_floating_blurred, shift=[current_flow_y, current_flow_x], mode='nearest')
                current_fog_clouds = shift(cloud_multiplier * grain_multiplier, shift=[current_flow_y, current_flow_x], mode='nearest')
                
                total_fake_dots = current_fake_static + current_fake_floating_shifted
                current_junk = debris_static + current_floating_debris + (total_fake_dots * config.ACTIVE_FND["PHOTON_YIELD"])
                
                fnd_light_off = (current_real_dots * config.ACTIVE_FND["PHOTON_YIELD"]) * laser_flicker * illum_profile
                fnd_light_on  = fnd_light_off * (1.0 - odmr_map)
                
                junk_light = current_junk * laser_bleach * laser_flicker * illum_profile
                base_fog = config.BACKGROUND_PHOTONS * illum_profile * current_fog_clouds * laser_bleach * laser_flicker
                
                off_pure = fnd_light_off + junk_light + base_fog
                fog_on = shift(base_fog, shift=[config.THERMAL_LENSING_SHIFT, 0], mode='nearest') if config.THERMAL_LENSING_SHIFT > 0 else base_fog
                on_pure = fnd_light_on + junk_light + fog_on
                
                dx = (config.DRIFT_PX * time_frac) + np.random.normal(0, 0.3)
                dy = (config.DRIFT_PX * time_frac) + np.random.normal(0, 0.3)
                
                def apply_camera_physics(pure_photon_img, sx, sy):
                    shifted = shift(pure_photon_img, shift=[sy, sx], mode='nearest')
                    shot_noise = np.random.normal(0, np.sqrt(np.clip(shifted, 0, None))) * config.EXCESS_SHOT_NOISE_MULTIPLIER
                    noisy_photons = np.clip(shifted + shot_noise, 0, None)
                    read_noise = np.random.normal(0, config.BACKGROUND_GRAININESS_STD, size=noisy_photons.shape)
                    if config.SENSOR_CROSSTALK > 0:
                        read_noise = gaussian_filter(read_noise, sigma=config.SENSOR_CROSSTALK)
                    noisy_photons = np.clip(noisy_photons + read_noise, 0, None)
                    scaled_intensity = np.clip((noisy_photons / config.CAMERA_SATURATION) * 255, 0, 255).astype(np.uint8)
                    
                    rgb_image = np.zeros((config.SIZE_Y, config.SIZE_X, 3), dtype=np.uint8)
                    rgb_image[:, :, 0] = scaled_intensity 
                    return rgb_image

                Image.fromarray(apply_camera_physics(off_pure, dx, dy), mode='RGB').save(os.path.join(off_dir, f"frame_{i:02d}_OFF.tif"))
                Image.fromarray(apply_camera_physics(on_pure, dx, dy), mode='RGB').save(os.path.join(on_dir, f"frame_{i:02d}_ON.tif"))
                
    print(f"✅ Simulation complete in {time.time() - start_time:.1f} seconds.")

if __name__ == "__main__":
    run_digital_twin_simulator()

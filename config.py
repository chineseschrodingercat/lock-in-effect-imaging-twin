# =====================================================================
# MASTER CONFIGURATION DASHBOARD
# =====================================================================

# --- 1. GLOBAL EXPERIMENT SETTINGS ---
DATA_ROOT = "data/raw_simulations/100nm"
TARGET_FND_COUNTS = [0, 1, 2, 5, 10, 25, 50, 100, 250, 500] 
NUM_REPLICATES = 3  
CYCLES = 25                       
SIZE_X, SIZE_Y = 960, 720         

# --- 2. PARTICLE MODE TOGGLE ---
PARTICLE_MODE = "100nm"  # Options: "100nm" or "600nm"
FND_PHYSICS = {
    "100nm": {"PHOTON_YIELD": 1000.0, "JUNK_COUNT": 200, "FAKE_FND_COUNT": 50},
    "600nm": {"PHOTON_YIELD": 25000.0, "JUNK_COUNT": 200, "FAKE_FND_COUNT": 50}
}
ACTIVE_FND = FND_PHYSICS[PARTICLE_MODE]

# --- 3. OPTICS & CAMERA PHYSICS ---
LENS_POWER = "40x_binned"         
PSF_SIGMA = 1.2                   
AIRY_RING_MULTIPLIER = 5.0        
VIGNETTING_STRENGTH = 0.4         
BACKGROUND_PHOTONS = 800.0        
BACKGROUND_CLOUDINESS = 0.4       
CAMERA_SATURATION = 4000.0        
BACKGROUND_GRAININESS_STD = 0.5   
ODMR_DROP = 0.02                  
SENSOR_CROSSTALK = 0.65           
EXCESS_SHOT_NOISE_MULTIPLIER = 1.2

# --- 4. THERMODYNAMICS & FLUID DYNAMICS ---
DRIFT_PX = 2.0                    
LASER_INSTABILITY = 0.02          
LASER_DIMMING = 0.15              
B1_MICROWAVE_GRADIENT = 0.25      
Z_AXIS_FOCAL_DRIFT = 0.2          
THERMAL_LENSING_SHIFT = 0.10      

FLOATING_DEBRIS_FRACTION = 0.3    
FLUID_FLOW_X = 1.5                
FLUID_FLOW_Y = -0.5               
BROWNIAN_WOBBLE_STD = 0.8         

BIO_GRAIN_SIZE = 1.2              
BIO_GRAIN_CONTRAST = 0.05         
CLUSTERING_PROBABILITY = 0.2      
JUNK_CLUSTERING_PROBABILITY = 0.5 
NUM_DEFOCUS_DONUTS = 1            
NUM_SALT_PEPPER_DUST = 800        

# --- 5. CLINICAL VALIDATION FILTERS ---
MIN_SIGNAL_RISE = 1.2

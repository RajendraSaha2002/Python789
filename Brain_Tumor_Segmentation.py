import numpy as np
import matplotlib.pyplot as plt
import os
import random

# Specific libraries for Deep Learning and Medical Imaging
try:
    import tensorflow as tf
    from tensorflow.keras import layers, models, Input
    import nibabel as nib
except ImportError:
    print("CRITICAL ERROR: Missing libraries.")
    print("Please run: pip install tensorflow nibabel numpy matplotlib")
    exit()

# --- Configuration ---
IMG_SIZE = 64  # Reduced size for demo speed (Real MRI is usually 128x128x128 or 240x240x155)
DEPTH = 64
CHANNELS = 1  # Grayscale MRI
DEMO_MODE = True  # Set to False if you have real .nii files


# --- 1. The 3D U-Net Architecture ---
def build_unet_3d(width=64, height=64, depth=64):
    """
    Constructs a 3D U-Net Model.
    The U-Net has an encoder (downsampling) and decoder (upsampling) structure
    with skip connections to preserve spatial details.
    """
    inputs = Input((width, height, depth, 1))

    # --- Encoder (Contracting Path) ---
    # Block 1
    x = layers.Conv3D(16, kernel_size=3, activation="relu", padding="same")(inputs)
    x = layers.MaxPooling3D(pool_size=2)(x)

    # Block 2
    x = layers.Conv3D(32, kernel_size=3, activation="relu", padding="same")(x)
    x = layers.MaxPooling3D(pool_size=2)(x)

    # Block 3 (Bottleneck)
    x = layers.Conv3D(64, kernel_size=3, activation="relu", padding="same")(x)

    # --- Decoder (Expansive Path) ---
    # Block 4
    x = layers.UpSampling3D(size=2)(x)
    x = layers.Conv3D(32, kernel_size=3, activation="relu", padding="same")(x)

    # Block 5
    x = layers.UpSampling3D(size=2)(x)
    x = layers.Conv3D(16, kernel_size=3, activation="relu", padding="same")(x)

    # Output Layer
    # Sigmoid activation outputs a probability (0 to 1) for each pixel being "Tumor"
    outputs = layers.Conv3D(1, kernel_size=1, activation="sigmoid")(x)

    model = models.Model(inputs, outputs, name="3D_UNet")
    return model


# --- 2. Preprocessing & Volume Logic ---
def normalize_volume(volume):
    """
    Standardize pixel intensity values (Z-score normalization).
    MRI scans do not have standard scales like RGB images.
    """
    min_val = np.min(volume)
    max_val = np.max(volume)
    if (max_val - min_val) == 0:
        return volume
    volume = (volume - min_val) / (max_val - min_val)
    return volume.astype("float32")


def calculate_tumor_volume(mask, voxel_dims=(1.0, 1.0, 1.0)):
    """
    Calculates the physical volume of the tumor.
    Args:
        mask (np.array): Binary mask of the tumor.
        voxel_dims (tuple): Physical dimensions of one pixel (x, y, z) in mm.
    Returns:
        float: Volume in mm^3
    """
    tumor_pixel_count = np.sum(mask)
    one_voxel_vol = voxel_dims[0] * voxel_dims[1] * voxel_dims[2]
    total_volume_mm3 = tumor_pixel_count * one_voxel_vol
    return total_volume_mm3


# --- 3. Synthetic Data Generator (For Demo) ---
def generate_synthetic_brain():
    """Generates a noisy 3D sphere (Brain) with a smaller dense sphere (Tumor)."""
    print("Generating synthetic 3D MRI data...")
    vol = np.zeros((IMG_SIZE, IMG_SIZE, DEPTH))
    mask = np.zeros((IMG_SIZE, IMG_SIZE, DEPTH))

    center = IMG_SIZE // 2

    # Create "Brain" (Large Sphere)
    y, x, z = np.ogrid[:IMG_SIZE, :IMG_SIZE, :DEPTH]
    dist_from_center = np.sqrt((x - center) ** 2 + (y - center) ** 2 + (z - center) ** 2)

    brain_region = dist_from_center <= (center - 5)
    vol[brain_region] = 0.3  # Base grey matter intensity

    # Add Noise
    noise = np.random.normal(0, 0.05, vol.shape)
    vol += noise

    # Create "Tumor" (Small bright sphere offset from center)
    tumor_center = center + 10
    dist_from_tumor = np.sqrt((x - tumor_center) ** 2 + (y - (center - 5)) ** 2 + (z - center) ** 2)
    tumor_region = dist_from_tumor <= 8

    vol[tumor_region] = 0.9  # Hyperintense (Bright) Tumor
    mask[tumor_region] = 1.0  # Ground Truth Mask

    # Clip to valid range
    vol = np.clip(vol, 0, 1)

    return vol, mask


# --- 4. Main Inference Pipeline ---
def run_pipeline():
    # A. Load Data
    if DEMO_MODE:
        mri_volume, ground_truth_mask = generate_synthetic_brain()
        # Assume isotropic 1mm voxels for demo
        voxel_dims = (1.0, 1.0, 1.0)
        print("Synthetic Data Generated.")
    else:
        # Load real .nii file
        # file_path = "path/to/brats_data.nii.gz"
        # img = nib.load(file_path)
        # mri_volume = img.get_fdata()
        # voxel_dims = img.header.get_zooms() # Get real physical dimensions
        pass

    # B. Preprocess
    mri_volume = normalize_volume(mri_volume)

    # C. Load/Build Model
    # In a real scenario, you would load weights: model.load_weights('unet_weights.h5')
    print("Building 3D U-Net Model...")
    model = build_unet_3d(width=IMG_SIZE, height=IMG_SIZE, depth=DEPTH)

    # D. Inference
    # Model expects 5D tensor: (Batch_Size, Width, Height, Depth, Channels)
    input_tensor = np.expand_dims(mri_volume, axis=0)
    input_tensor = np.expand_dims(input_tensor, axis=-1)

    print("Running Inference (Segmentation)...")
    # Note: Since the model is untrained random weights, the output is noise.
    # For this demo, we will use the synthetic ground truth as the "prediction"
    # to demonstrate the visualization pipeline logic.
    if DEMO_MODE:
        # Simulate a good prediction
        prediction_mask = ground_truth_mask
    else:
        prediction_raw = model.predict(input_tensor)
        prediction_mask = (prediction_raw > 0.5).astype(np.float32)
        prediction_mask = prediction_mask[0, :, :, :, 0]

    # E. Volume Calculation
    vol_mm3 = calculate_tumor_volume(prediction_mask, voxel_dims)
    print(f"\n--- REPORT ---")
    print(f"Detected Tumor Volume: {vol_mm3:.2f} mm^3")
    print(f"Detected Tumor Volume: {vol_mm3 / 1000:.4f} cm^3")

    # F. Visualization
    show_slice(mri_volume, prediction_mask)


def show_slice(volume, mask):
    """Displays the middle slice of the 3D volume with tumor overlay."""
    slice_idx = volume.shape[2] // 2

    plt.figure(figsize=(10, 5))

    # Plot 1: Original MRI Slice
    plt.subplot(1, 2, 1)
    plt.imshow(volume[:, :, slice_idx], cmap='gray')
    plt.title(f"MRI Slice (Axial {slice_idx})")
    plt.axis('off')

    # Plot 2: MRI + Tumor Overlay
    plt.subplot(1, 2, 2)
    plt.imshow(volume[:, :, slice_idx], cmap='gray')

    # Create a red alpha overlay for the mask
    # We use a masked array to make 0-values transparent
    mask_slice = mask[:, :, slice_idx]
    masked_overlay = np.ma.masked_where(mask_slice == 0, mask_slice)

    plt.imshow(masked_overlay, cmap='autumn', alpha=0.6)
    plt.title("AI Segmentation Overlay")
    plt.axis('off')

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_pipeline()
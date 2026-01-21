import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt


# --- 1. Synthetic Data Generation ---
# In a real scenario, you would use nibabel to load .nii files:
# import nibabel as nib
# img = nib.load('patient_scan.nii')

def generate_synthetic_brains(size=128):
    """
    Generates two 3D images:
    1. Fixed Image (The Atlas): A centered ellipsoid.
    2. Moving Image (The Patient): The same ellipsoid but rotated, translated, and distorted.
    """
    print("Generating synthetic 3D Brain data...")

    # Grid generation
    grid = np.mgrid[:size, :size, :size]
    center = size / 2

    # Equation for an Ellipsoid (Approximating a brain shape)
    # (x-cx)^2/a^2 + (y-cy)^2/b^2 + (z-cz)^2/c^2 <= 1
    # We add some internal "structure" (noise) to give the algorithm texture to latch onto.

    dist_sq = ((grid[0] - center) / 30) ** 2 + \
              ((grid[1] - center) / 40) ** 2 + \
              ((grid[2] - center) / 30) ** 2

    # Create Binary Mask -> Float Image
    volume = (dist_sq <= 1.0).astype(np.float32)

    # Add "Tissue Texture" (Random Noise inside the brain area)
    # Mutual Information metrics need intensity variation, not just binary shapes.
    noise = np.random.normal(0, 0.1, volume.shape)
    volume[volume > 0] += noise[volume > 0]

    # Convert to SimpleITK Image
    fixed_image = sitk.GetImageFromArray(volume)

    # --- Create the "Moving" Image (Simulate Misalignment) ---
    # We apply a known transform to the Fixed image to create the Moving image.
    # In a real clinical case, this is the patient's scan which is naturally misaligned.

    # 1. Rotate 20 degrees, Shift 10 pixels
    transform = sitk.Euler3DTransform()
    transform.SetCenter(fixed_image.TransformContinuousIndexToPhysicalPoint([center, center, center]))
    transform.SetRotation(0.3, 0.0, 0.1)  # Rotation in Radians (approx 17 degrees)
    transform.SetTranslation((10, -5, 5))

    # Resample the fixed image using this transform to create the moving image
    moving_image = sitk.Resample(fixed_image, fixed_image, transform, sitk.sitkLinear, 0.0, fixed_image.GetPixelID())

    return fixed_image, moving_image


# --- 2. The Registration Engine ---

def register_images(fixed_image, moving_image):
    """
    Performs intensity-based image registration using SimpleITK.
    Goal: Find the transform that maps Moving -> Fixed.
    """
    print("Initializing Registration Algorithm...")

    # A. Initialization
    # Start by aligning the geometric centers of the images.
    # This helps prevents the optimizer from getting stuck in local minima.
    initial_transform = sitk.CenteredTransformInitializer(
        fixed_image,
        moving_image,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY
    )

    # B. Set up the Registration Method
    registration_method = sitk.ImageRegistrationMethod()

    # Metric: Mattes Mutual Information
    # Measures how "correlated" the intensities are. Robust for multi-modal images (e.g., CT to MRI).
    registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(0.1)  # Sample 10% of voxels for speed

    # Optimizer: Gradient Descent
    # "Walks down" the error landscape to find the best fit.
    registration_method.SetOptimizerAsGradientDescent(
        learningRate=1.0,
        numberOfIterations=100,
        convergenceMinimumValue=1e-6,
        convergenceWindowSize=10
    )

    # Interpolator: Linear
    registration_method.SetInterpolator(sitk.sitkLinear)

    # Set Initial Transform
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    # C. Execute
    print("Optimizing alignment (Gradient Descent)...")
    final_transform = registration_method.Execute(fixed_image, moving_image)

    print(f"Final Metric Value: {registration_method.GetMetricValue():.4f}")
    print(f"Optimizer Stopping Condition: {registration_method.GetOptimizerStopConditionDescription()}")

    return final_transform


# --- 3. Visualization Tools ---

def show_slice_overlay(fixed, moving, title, z_slice=None):
    """
    Visualizes the result by overlaying the images.
    Fixed = Green
    Moving = Magenta
    Overlap = White (Green + Magenta)
    """
    # Convert to Numpy
    fixed_arr = sitk.GetArrayFromImage(fixed)
    moving_arr = sitk.GetArrayFromImage(moving)

    if z_slice is None:
        z_slice = fixed_arr.shape[0] // 2

    f_slice = fixed_arr[z_slice, :, :]
    m_slice = moving_arr[z_slice, :, :]

    # Normalize to 0-1 for plotting
    f_slice = (f_slice - f_slice.min()) / (f_slice.max() - f_slice.min())
    m_slice = (m_slice - m_slice.min()) / (m_slice.max() - m_slice.min())

    # Create RGB Image
    # R = Moving (Magenta component)
    # G = Fixed (Green component)
    # B = Moving (Magenta component)
    # Result: Fixed is Green, Moving is Magenta.
    # If they overlap perfectly: (1, 0, 1) + (0, 1, 0) = (1, 1, 1) -> White/Gray

    rgb_image = np.zeros((f_slice.shape[0], f_slice.shape[1], 3))
    rgb_image[..., 0] = m_slice  # Red
    rgb_image[..., 1] = f_slice  # Green
    rgb_image[..., 2] = m_slice  # Blue

    plt.imshow(rgb_image)
    plt.title(title)
    plt.axis('off')


def main():
    # 1. Generate Data
    fixed_img, moving_img = generate_synthetic_brains()

    # 2. Visualize Before Registration
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    show_slice_overlay(fixed_img, moving_img, "Before Registration\n(Misaligned)")

    # 3. Register
    transform = register_images(fixed_img, moving_img)

    # 4. Apply Transform to Moving Image (Resample)
    # This actually moves the patient pixels into the atlas coordinate space
    resampled_moving = sitk.Resample(
        moving_img,
        fixed_img,
        transform,
        sitk.sitkLinear,
        0.0,
        moving_img.GetPixelID()
    )

    # 5. Visualize After Registration
    plt.subplot(1, 2, 2)
    show_slice_overlay(fixed_img, resampled_moving, "After Registration\n(Aligned)")

    print("\nDisplaying results...")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
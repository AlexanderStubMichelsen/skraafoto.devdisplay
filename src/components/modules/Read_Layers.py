import tifffile

# Load the TIFF file
tiff_file = tifffile.TiffFile('./2021_84_40_2_0031_00070238.tif')

# Check the number of pages (layers) in the TIFF file
num_layers = len(tiff_file.pages)

print(f'The TIFF file contains {num_layers} layer(s).')

# Optional: you can also inspect each layer
for i, page in enumerate(tiff_file.pages):
    print(f"Layer {i+1}: Shape {page.shape}, Data Type: {page.dtype}")

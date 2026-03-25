# 🖼️ PixelCraft

**High-Performance Spatial Imagery & Raster Manipulation Toolkit**

**P**ixel **I**magery **X**-transformation **E**ngine for **L**ayers — **C**ontextual **R**aster **A**nalysis & **F**eature **T**oolkit.


## 🚀 Overview
**PixelCraft** is a specialized Python library designed to handle the "heavy lifting" of raster data processing. Unlike standard image processing libraries, PixelCraft is strictly **spatial-aware**, ensuring that every transformation—from simple cropping to complex spectral math—preserves essential geographic metadata, coordinate reference systems (CRS), and affine transformations.

This toolkit is built for GIS developers who need to move beyond desktop GIS software into automated, scalable imagery ETL (Extract, Transform, Load) pipelines.

---

## 🛠️ Core Capabilities

### 1. Spatial Slicing & Dicing
Automated clipping and masking of high-resolution rasters using vector geometries. PixelCraft manages the alignment of pixel grids to ensure zero-offset results when integrating with vector datasets.

### 2. Spectral Engine
A robust framework for multi-spectral band math. 
*   **Standard Indices:** Out-of-the-box support for NDVI, NDWI, and NBR.
*   **Custom Ratios:** A flexible API for defining custom band calculations across diverse sensor types (Landsat, Sentinel, etc.).

### 3. Raster Sanitization
Tools for handling the "messy" side of imagery:
*   **NoData Management:** Sophisticated interpolation and masking for missing data.
*   **Resampling Logic:** High-fidelity resampling (Bilinear, Cubic, Lanczos) that respects the underlying data type and bit depth.

---

## 🏗️ Technical Architecture
PixelCraft leverages industry-standard libraries to ensure maximum performance and compatibility:
*   **Rasterio / GDAL:** For low-level data I/O and metadata preservation.
*   **NumPy:** For vectorized array operations and high-speed pixel manipulation.
*   **GeoPandas:** For seamless vector-to-raster interaction.

---

## 📂 Project Structure
```text
PixelCraft/
├── src/
│   ├── engine/                # Core raster processing logic
│   ├── spectral/              # Band math and indices
│   └── utils/                 # Metadata and CRS helpers
├── example/                   # Sample notebooks and test data
├── tests/                     # Unit tests for pixel accuracy
├── README.md
└── LICENSE

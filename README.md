# RailSense™ | National Railway Asset Protection & Telemetry Suite

An industrial-grade, real-time track integrity monitoring and early derailment prevention system designed for high-density rail corridors.

## 🚀 Core Component Architecture

* **/ (Root Directory):** High-fidelity Industrial Mission Control Dashboard built with Leaflet GIS spatial mapping and Chart.js triaxial harmonic decomposition charts. Deployable directly via static hosting environments (GitHub Pages, Vercel).
* **/backend:** Core Data Ingestion Signal Processing Pipeline (`anomaly_detector.py`) executing time-domain feature extractions (Root Mean Square acceleration and Kurtosis coefficients) to detect ballast degradation, thermal buckling, and track fractures.
* **/hardware:** Production-ready OpenSCAD industrial axle-journal protective enclosure blueprints (`enclosure.scad`) engineered to secure edge nodes against severe high-vibration operational environments.

## 🛠️ Local Server Deployment

To run the localized processing environment pipeline:

```bash
# Install required scientific computation dependencies
pip install numpy scipy

# Initialize the main telemetry routing node backend
python backend/main.py
```

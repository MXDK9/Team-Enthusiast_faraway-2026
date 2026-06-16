import numpy as np
import scipy.stats as stats

class StructuralVibrationEngine:
    """
    Processes high-frequency continuous streaming arrays received 
    from edge nodes for systemic track structural integrity calculation.
    """
    def __init__(self, buffer_window_size=200):
        self.window_size = buffer_window_size

    def analyze_vibration_window(self, data_array):
        """
        Executes real-time signal analysis. 
        Detects track structural fracturing or localized ballast shifting events.
        """
        signal = np.array(data_array)
        if len(signal) == 0:
            return {"rms_acceleration": 0.0, "kurtosis_factor": 3.0, "peak_g_force": 0.0, "critical_event": False}

        # 1. Root Mean Square (RMS) calculation for total mechanical energy signature
        rms = np.sqrt(np.mean(signal ** 2))

        # 2. Kurtosis evaluation for localized structural impact shocks
        kurtosis = stats.kurtosis(signal, fisher=False)

        # 3. Peak Absolute Amplitude metric extraction
        peak_g = np.max(np.abs(signal))

        # Core operational safety condition parsing 
        # Kurtosis spikes above 4.5 indicate localized physical structural cracks
        is_critical = bool(kurtosis > 4.5 or rms > 3.2)

        return {
            "rms_acceleration": round(float(rms), 4),
            "kurtosis_factor": round(float(kurtosis), 4),
            "peak_g_force": round(float(peak_g), 4),
            "critical_event": is_critical
        }

if __name__ == "__main__":
    detector = StructuralVibrationEngine()
    # Continuous sensor telemetry simulation array
    nominal_track_vibration = np.random.normal(0, 0.45, 200)
    
    # Introduce structural crack collision signature spike
    nominal_track_vibration[120] = 5.8 
    
    analysis_output = detector.analyze_vibration_window(nominal_track_vibration)
    print(f"Operational Analytics Process Test Output:\n{analysis_output}")

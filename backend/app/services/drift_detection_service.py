import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from typing import Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler

class Autoencoder(nn.Module):
    def __init__(self, input_dim: int, encoding_dim: int = 8):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, encoding_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

class DriftDetectionService:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None
        self.threshold = None

    @staticmethod
    def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        """
        Calculate Population Stability Index (PSI).
        PSI < 0.1: No significant drift
        PSI < 0.2: Moderate drift
        PSI >= 0.2: Significant drift
        """
        def scale_range(input, min, max):
            input += -(np.min(input))
            input /= np.max(input) / (max - min)
            input += min
            return input

        breakpoints = np.arange(0, buckets + 1) / (buckets) * 100
        
        if len(expected) == 0 or len(actual) == 0:
            return 0.0

        expected_percents = np.percentile(expected, breakpoints)
        actual_percents = np.percentile(actual, breakpoints)

        expected_percents[0] = -np.inf
        expected_percents[-1] = np.inf

        # Calculate counts in each bucket
        expected_counts = np.histogram(expected, expected_percents)[0]
        actual_counts = np.histogram(actual, expected_percents)[0]

        # Avoid division by zero
        expected_counts = np.where(expected_counts == 0, 0.0001, expected_counts)
        actual_counts = np.where(actual_counts == 0, 0.0001, actual_counts)

        expected_ratios = expected_counts / len(expected)
        actual_ratios = actual_counts / len(actual)

        psi = np.sum((actual_ratios - expected_ratios) * np.log(actual_ratios / expected_ratios))
        return float(psi)

    @staticmethod
    def detect_drift_statistical(reference_data: List[float], current_data: List[float]) -> Dict[str, Any]:
        """
        Perform KS Test and PSI to detect drift.
        """
        ref = np.array(reference_data)
        curr = np.array(current_data)

        # KS Test
        ks_stat, p_value = ks_2samp(ref, curr)
        drift_detected_ks = p_value < 0.05

        # PSI
        psi_value = DriftDetectionService.calculate_psi(ref, curr)
        drift_detected_psi = psi_value > 0.2

        return {
            "ks_test": {
                "statistic": float(ks_stat),
                "p_value": float(p_value),
                "drift_detected": bool(drift_detected_ks)
            },
            "psi": {
                "value": psi_value,
                "drift_detected": bool(drift_detected_psi)
            },
            "overall_drift": bool(drift_detected_ks or drift_detected_psi)
        }

    def train_autoencoder(self, data: np.ndarray, epochs: int = 50):
        """
        Train an autoencoder on reference data to learn the normal regime.
        """
        # Normalize data
        scaled_data = self.scaler.fit_transform(data)
        tensor_data = torch.FloatTensor(scaled_data)
        
        input_dim = data.shape[1]
        self.model = Autoencoder(input_dim)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.01)

        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(tensor_data)
            loss = criterion(outputs, tensor_data)
            loss.backward()
            optimizer.step()

        # Set threshold based on reconstruction error on training data
        self.model.eval()
        with torch.no_grad():
            reconstructions = self.model(tensor_data)
            loss = torch.mean((tensor_data - reconstructions) ** 2, dim=1)
            self.threshold = np.percentile(loss.numpy(), 95) # 95th percentile as threshold

        return {"status": "trained", "threshold": float(self.threshold), "final_loss": float(loss.mean())}

    def detect_anomalies_autoencoder(self, data: np.ndarray) -> Dict[str, Any]:
        """
        Detect anomalies using the trained autoencoder.
        """
        if self.model is None:
            return {"error": "Model not trained"}

        scaled_data = self.scaler.transform(data)
        tensor_data = torch.FloatTensor(scaled_data)
        
        self.model.eval()
        with torch.no_grad():
            reconstructions = self.model(tensor_data)
            loss = torch.mean((tensor_data - reconstructions) ** 2, dim=1).numpy()

        anomalies = loss > self.threshold
        anomaly_ratio = np.sum(anomalies) / len(anomalies)

        return {
            "anomaly_detected": bool(anomaly_ratio > 0.1), # If >10% data is anomalous
            "anomaly_ratio": float(anomaly_ratio),
            "mean_reconstruction_error": float(np.mean(loss)),
            "threshold": float(self.threshold)
        }

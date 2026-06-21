from abc import ABC, abstractmethod
import pandas as pd


class DataRepository(ABC):
    @abstractmethod
    def load_all(self) -> pd.DataFrame:
        """Return all measurement data as a DataFrame."""

    @abstractmethod
    def get_for_parameter(self, parameter: str) -> pd.DataFrame:
        """Return rows for a single parameter (e.g. Metric A)."""

    @abstractmethod
    def append_batch(self, batch_id: str, date: str, formula: str,
                     measurements: dict[str, dict]) -> None:
        """Append one batch to storage.

        measurements = {
            'pH':  {'reps': [6.82, 6.91, 6.78], 'lower_spec': 5.50, 'upper_spec': 8.50},
            'IV':  {'reps': [0.952, 0.947, 0.961], 'lower_spec': 0.90, 'upper_spec': 1.10},
            ...
        }
        """

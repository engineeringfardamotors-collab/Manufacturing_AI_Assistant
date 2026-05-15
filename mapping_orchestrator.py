import pandas as pd

from services.engine.file_type_detector import FileTypeDetector
from services.engine.mapping_engine import MappingEngine
from services.engine.normalizer import DataNormalizer


class MappingOrchestrator:
    def __init__(self):
        self.file_type_detector = FileTypeDetector()
        self.mapping_engine = MappingEngine()
        self.normalizer = DataNormalizer()

    def process(self, df: pd.DataFrame) -> dict:
        file_type_result = self.file_type_detector.detect(df.columns)
        detected_columns = self.mapping_engine.detect_columns(df.columns)
        normalized_df = self.normalizer.normalize_dataframe(df, detected_columns)

        return {
            "file_type": file_type_result["detected_type"],
            "file_type_scores": file_type_result["scores"],
            "detected_columns": detected_columns,
            "normalized_df": normalized_df,
        }

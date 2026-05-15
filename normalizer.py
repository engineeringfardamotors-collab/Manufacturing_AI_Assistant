import pandas as pd


class DataNormalizer:
    STANDARD_FIELDS = [
        "part_number",
        "description",
        "quantity",
        "alternative_part",
    ]

    def normalize_dataframe(self, df: pd.DataFrame, detected_columns: dict) -> pd.DataFrame:
        rename_map = {}

        for standard_name, original_name in detected_columns.items():
            rename_map[original_name] = standard_name

        normalized_df = df.rename(columns=rename_map).copy()

        existing_fields = [
            field for field in self.STANDARD_FIELDS
            if field in normalized_df.columns
        ]

        return normalized_df[existing_fields]

class MappingEngine:
    COLUMN_ALIASES = {
        "part_number": [
            "part no",
            "part number",
            "part_number",
            "material",
            "material no",
            "material number",
            "internal material no",
            "mpn",
            "mpn number",
        ],
        "quantity": [
            "qty",
            "quantity",
            "usage qty",
            "component qty",
            "required qty",
        ],
        "description": [
            "description",
            "part description",
            "material description",
            "component description",
        ],
        "alternative_part": [
            "alternative part",
            "alternate part",
            "alt part",
            "substitute part",
            "replacement part",
            "mpn alt",
            "alternative material",
        ],
    }

    def normalize_column_name(self, column_name: str) -> str:
        return str(column_name).strip().lower().replace("_", " ")

    def detect_columns(self, columns):
        normalized_map = {
            col: self.normalize_column_name(col)
            for col in columns
        }

        detected = {}

        for standard_name, aliases in self.COLUMN_ALIASES.items():
            for original_col, normalized_col in normalized_map.items():
                if normalized_col in aliases:
                    detected[standard_name] = original_col
                    break

        return detected

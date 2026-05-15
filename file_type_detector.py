class FileTypeDetector:
    FILE_TYPE_KEYWORDS = {
        "bom": [
            "bom",
            "bill of material",
            "component",
            "usage qty",
            "component qty",
        ],
        "balance": [
            "balance",
            "line balance",
            "station",
            "process",
            "operation",
            "required qty",
        ],
        "packing_list": [
            "packing",
            "packing list",
            "case no",
            "package no",
            "invoice",
            "shipment",
            "gross weight",
            "net weight",
        ],
        "mpn": [
            "mpn",
            "mpn number",
            "alternative part",
            "alternate part",
            "substitute part",
            "replacement part",
            "alternative material",
        ],
    }

    def normalize_text(self, value: str) -> str:
        return str(value).strip().lower().replace("_", " ")

    def detect(self, columns):
        normalized_columns = [self.normalize_text(col) for col in columns]

        scores = {file_type: 0 for file_type in self.FILE_TYPE_KEYWORDS}

        for file_type, keywords in self.FILE_TYPE_KEYWORDS.items():
            for column in normalized_columns:
                for keyword in keywords:
                    if keyword in column:
                        scores[file_type] += 1

        best_type = max(scores, key=scores.get)

        if scores[best_type] == 0:
            return {
                "detected_type": "unknown",
                "scores": scores,
            }

        return {
            "detected_type": best_type,
            "scores": scores,
        }

import pandas as pd
from pathlib import Path


class SapMpnReader:
    """
    Reader برای فایل SAP MPN Export.
    ستون‌های کلیدی:
        - MPN              : شماره فنی MPN / جایگزین (مثل 10107481-L01)
        - Int. material no.: شماره فنی Internal / پایه (مثل 10107481)
        - Material Description: نام قطعه
        - X-Plant Material Status: وضعیت (اگر خالی = فعال)
    """

    MPN_COL = "MPN"
    INTERNAL_COL = "Int. material no."
    DESC_COL = "Material Description"
    STATUS_COL = "X-Plant Material Status"
    SHEET_NAME = "MPN"

    def read(self, file) -> pd.DataFrame:
        """
        خواندن فایل MPN و برگرداندن DataFrame نرمال‌شده.
        خروجی: DataFrame با ستون‌های:
            mpn_part     : شماره MPN (جایگزین)
            internal_part: شماره Internal (پایه)
            description  : نام قطعه
            is_active    : آیا فعال است (True/False)
        """
        xls = pd.ExcelFile(file)

        # پیدا کردن شیت MPN
        target_sheet = None
        for sh in xls.sheet_names:
            if sh.strip().upper() == self.SHEET_NAME.upper():
                target_sheet = sh
                break
        if target_sheet is None:
            target_sheet = xls.sheet_names[0]

        raw = pd.read_excel(file, sheet_name=target_sheet, header=0)

        # بررسی وجود ستون‌های کلیدی
        missing_cols = [c for c in [self.MPN_COL, self.INTERNAL_COL] if c not in raw.columns]
        if missing_cols:
            raise ValueError(f"ستون‌های زیر در فایل MPN پیدا نشدند: {missing_cols}")

        def clean(x) -> str:
            if pd.isna(x):
                return ""
            return str(x).strip().strip("'").strip()

        df = pd.DataFrame({
            "mpn_part": raw[self.MPN_COL].apply(clean),
            "internal_part": raw[self.INTERNAL_COL].apply(clean),
            "description": raw[self.DESC_COL].apply(clean) if self.DESC_COL in raw.columns else "",
            "is_active": raw[self.STATUS_COL].isna() if self.STATUS_COL in raw.columns else True,
        })

        # حذف ردیف‌های خالی
        df = df[(df["mpn_part"] != "") & (df["internal_part"] != "")].copy()
        df = df.reset_index(drop=True)

        return df

    def build_lookup(self, df: pd.DataFrame) -> dict:
        """
        ساخت dict lookup برای resolver:
        {
          mpn_part -> internal_part,   (مثل "10107481-L01" -> "10107481")
          internal_part -> [mpn_parts] (مثل "10107481" -> ["10107481-L01"])
        }
        """
        mpn_to_internal = {}
        internal_to_mpns = {}

        for _, row in df.iterrows():
            if not row["is_active"]:
                continue
            mpn = row["mpn_part"]
            internal = row["internal_part"]

            if mpn and internal:
                mpn_to_internal[mpn] = internal
                internal_to_mpns.setdefault(internal, []).append(mpn)

        return {
            "mpn_to_internal": mpn_to_internal,
            "internal_to_mpns": internal_to_mpns,
        }

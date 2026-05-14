import json
import tempfile
from pathlib import Path
import unittest
from typing import Optional

from datablaster import (
    compare_profiles,
    profile_csv,
    profile_pandas_dataframe,
    profile_spark_dataframe,
    write_json_report,
    write_output,
)


class FakeSeriesStrAccessor:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def strip(self) -> "FakeSeries":
        return FakeSeries([value.strip() for value in self._values])


class FakeSeries:
    def __init__(self, values: list[Optional[str]]) -> None:
        self._values = values
        self.str = FakeSeriesStrAccessor([value or "" for value in values])

    def notna(self) -> "FakeSeriesMask":
        return FakeSeriesMask([value is not None and value != "" for value in self._values])

    def astype(self, _type: object) -> "FakeSeries":
        return FakeSeries(["" if value is None else str(value) for value in self._values])

    def dropna(self) -> "FakeSeries":
        return FakeSeries([value for value in self._values if value is not None and value != ""])

    def nunique(self) -> int:
        return len({value for value in self._values if value is not None and value != ""})

    def head(self, size: int) -> "FakeSeries":
        return FakeSeries(self._values[:size])

    def tolist(self) -> list[str]:
        return ["" if value is None else str(value) for value in self._values]

    def __eq__(self, other: object) -> "FakeSeriesMask":
        return FakeSeriesMask([value == other for value in self._values])


class FakeSeriesMask:
    def __init__(self, values: list[bool]) -> None:
        self._values = values

    def sum(self) -> int:
        return sum(1 for value in self._values if value)


class FakePandasFrame:
    def __init__(self, columns: dict[str, list[Optional[str]]]) -> None:
        self._columns = columns
        self.columns = list(columns)

    def __getitem__(self, name: str) -> FakeSeries:
        return FakeSeries(self._columns[name])

    def __len__(self) -> int:
        if not self.columns:
            return 0
        return len(self._columns[self.columns[0]])


class FakeSparkFrame:
    def __init__(self, pandas_frame: FakePandasFrame) -> None:
        self._pandas_frame = pandas_frame

    def toPandas(self) -> FakePandasFrame:
        return self._pandas_frame


class ProfileCsvTests(unittest.TestCase):
    def test_profiles_row_and_column_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text(
                "name,city\nAlice,NY\nAlice,\n,LA\nBob,NY\n",
                encoding="utf-8",
            )

            profile = profile_csv(csv_path)

            self.assertEqual(profile.row_count, 4)
            self.assertEqual(len(profile.columns), 2)

            name_column = profile.columns[0]
            city_column = profile.columns[1]

            self.assertEqual(name_column.name, "name")
            self.assertEqual(name_column.inferred_type, "text")
            self.assertEqual(name_column.non_null, 3)
            self.assertEqual(name_column.blank, 1)
            self.assertEqual(name_column.unique, 2)
            self.assertEqual(name_column.sample_values, ["Alice", "Bob"])

            self.assertEqual(city_column.name, "city")
            self.assertEqual(city_column.inferred_type, "text")
            self.assertEqual(city_column.non_null, 3)
            self.assertEqual(city_column.blank, 1)
            self.assertEqual(city_column.unique, 2)
            self.assertEqual(city_column.sample_values, ["NY", "LA"])

    def test_infers_common_column_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "typed.csv"
            csv_path.write_text(
                "id,score,active,created,name\n1,1.5,true,2026-05-14,Alice\n2,2.75,false,2026-05-15,Bob\n",
                encoding="utf-8",
            )

            profile = profile_csv(csv_path)

            self.assertEqual([column.inferred_type for column in profile.columns], ["integer", "float", "boolean", "date", "text"])


class WriteOutputTests(unittest.TestCase):
    def test_writes_json_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text("name\nAlice\n", encoding="utf-8")

            profile = profile_csv(csv_path)
            output_path = Path(temp_dir) / "profile.json"

            with output_path.open("w", encoding="utf-8") as handle:
                write_output(profile, handle)

            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["row_count"], 1)
            self.assertEqual(payload["column_count"], 1)
            self.assertEqual(payload["columns"][0]["name"], "name")
            self.assertEqual(payload["columns"][0]["inferred_type"], "text")


class CompareProfilesTests(unittest.TestCase):
    def test_reports_schema_drift_and_column_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir) / "baseline.csv"
            current_path = Path(temp_dir) / "current.csv"

            baseline_path.write_text(
                "name,city\nAlice,NY\nBob,LA\n",
                encoding="utf-8",
            )
            current_path.write_text(
                "name,state\nAlice,CA\nCara,TX\n",
                encoding="utf-8",
            )

            baseline = profile_csv(baseline_path)
            current = profile_csv(current_path)

            report = compare_profiles(current, baseline)

            self.assertEqual(report["row_count_delta"], 0)
            self.assertEqual(report["schema_drift"]["added_columns"], ["state"])
            self.assertEqual(report["schema_drift"]["removed_columns"], ["city"])
            self.assertEqual(report["summary"]["added_column_count"], 1)
            self.assertEqual(report["summary"]["removed_column_count"], 1)
            self.assertEqual(report["summary"]["changed_column_count"], 1)
            self.assertEqual(report["summary"]["type_changed_column_count"], 0)
            self.assertEqual(report["column_changes"][0]["name"], "name")
            self.assertTrue(report["column_changes"][0]["delta"]["sample_values_changed"])

    def test_reports_type_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir) / "baseline.csv"
            current_path = Path(temp_dir) / "current.csv"

            baseline_path.write_text("value\n1\n2\n", encoding="utf-8")
            current_path.write_text("value\nalpha\nbeta\n", encoding="utf-8")

            report = compare_profiles(profile_csv(current_path), profile_csv(baseline_path))

            self.assertEqual(report["summary"]["type_changed_column_count"], 1)
            self.assertEqual(report["type_changes"], [{"name": "value", "current_type": "text", "baseline_type": "integer"}])
            self.assertTrue(report["column_changes"][0]["delta"]["inferred_type_changed"])

    def test_writes_comparison_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir) / "baseline.csv"
            current_path = Path(temp_dir) / "current.csv"
            output_path = Path(temp_dir) / "report.json"

            baseline_path.write_text("name\nAlice\n", encoding="utf-8")
            current_path.write_text("name\nBob\n", encoding="utf-8")

            report = compare_profiles(profile_csv(current_path), profile_csv(baseline_path))

            with output_path.open("w", encoding="utf-8") as handle:
                write_json_report(report, handle)

            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["current_path"], str(current_path))
            self.assertEqual(payload["baseline_path"], str(baseline_path))
            self.assertEqual(payload["summary"]["changed_column_count"], 1)


class DataFrameApiTests(unittest.TestCase):
    def test_profiles_pandas_style_dataframe(self) -> None:
        frame = FakePandasFrame(
            {
                "name": ["Alice", "Alice", None, "Bob"],
                "city": ["NY", None, "LA", "NY"],
            }
        )

        profile = profile_pandas_dataframe(frame)

        self.assertEqual(profile.path, "<pandas-dataframe>")
        self.assertEqual(profile.row_count, 4)
        self.assertEqual(profile.columns[0].inferred_type, "text")
        self.assertEqual(profile.columns[0].sample_values, ["Alice", "Bob"])
        self.assertEqual(profile.columns[1].sample_values, ["NY", "LA"])

    def test_profiles_spark_style_dataframe_via_topandas(self) -> None:
        frame = FakeSparkFrame(
            FakePandasFrame(
                {
                    "name": ["Alice", "Alice", None, "Bob"],
                    "city": ["NY", None, "LA", "NY"],
                }
            )
        )

        profile = profile_spark_dataframe(frame)

        self.assertEqual(profile.path, "<spark-dataframe>")
        self.assertEqual(profile.row_count, 4)
        self.assertEqual(profile.columns[0].inferred_type, "text")
        self.assertEqual(profile.columns[0].unique, 2)


if __name__ == "__main__":
    unittest.main()
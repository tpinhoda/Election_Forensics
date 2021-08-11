import json
from os.path import join
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
from src.election import Election

@dataclass
class Processed(Election):
    aggregation_level: str = None
    candidacy_pos: str = None
    candidates: str = None
    levenshtein_threshold: float = None
    precision_filter: List[str] = field(default_factory=list)
    city_limits_filter: List[str] = field(default_factory=list)
    __data: pd.DataFrame = field(default_factory=pd.DataFrame)
    __data_info: Dict = field(default_factory=dict)
    __per: Optional[int] = None

    def init_logger_name(self):
        """Initialize the logger name"""
        self.logger_name = "Results (Processed)"

    def init_state(self):
        """Initialize the  process state name"""
        self.state = "processed"

    def _make_folders(self):
        """Make the initial folders"""
        self._make_initial_folders()
        self._mkdir(self.data_name)
        self._mkdir(self.aggregation_level)
        self._mkdir(self.candidacy_pos.lower())

    def _read_data_csv(self) -> pd.DataFrame:
        """Read the data.csv file and returns a pandas dataframe"""
        filepath = join(
            self._get_process_folder_path(state="interim"),
            self.data_name,
            self.aggregation_level,
            self.candidacy_pos,
            "data.csv",
        )
        self.__data = pd.read_csv(filepath).infer_objects()

    def _get_candidates_cols(self):
        return [col for col in self.__data if "CANDIDATE" in col]

    def _get_data_info(self):
        candidate_cols = self._get_candidates_cols()
        self.__data_info["size"] = len(self.__data)
        self.__data_info["turnout"] = self.__data["[ELECTION]_TURNOUT"].sum()
        self.__data_info["candidates_votes"] = {
            col: self.__data[col].sum() for col in candidate_cols
        }
        self.__data_info["null_votes"] = self.__data["[ELECTION]_NULL"]
        self.__data_info["null_blank"] = self.__data["[ELECTION]_BLANK"]

    def _filter_data(self):
        self.__data = self.__data[
            self.__data["[GEO]_LEVENSHTEIN_SIMILARITY"] >= self.levenshtein_threshold
        ]
        self.__data = self.__data[
            self.__data["[GEO]_CITY_LIMITS"].isin(self.city_limits_filter)
        ]
        self.__data = self.__data[
            self.__data["[GEO]_PRECISION"].isin(self.precision_filter)
        ]

    def _calculate_per(self) -> int:
        original_turnout = self.__data_info["turnout"]
        filtered_turnout = self.__data["[ELECTION]_TURNOUT"].sum()
        self.__per = 100 * filtered_turnout / original_turnout

    def _make_per_fold(self):
        self._mkdir("{:.2f}".format(self.__per))

    def _save_data(self):
        self.__data.to_csv(join(self.cur_dir, "data.csv"), index=False)

    def _generate_report(self):
        report_dict = {
            "Levenshtein Threshold": str(self.levenshtein_threshold),
            "City Limits": self.city_limits_filter,
            "Precisions": self.precision_filter,
            "Candidates": self.candidates,
            "#Rows": f"{len(self.__data)} ({100 * len(self.__data) / self.__data_info['size']}%)",
        }

        with open(join(self.cur_dir, "parameters.json"), "w") as fp:
            json.dump(report_dict, fp, indent=4)

    def run(self):
        """Run process"""
        self.init_logger_name()
        self.init_state()
        self.logger_info("Generating processed data.")
        self._make_folders()
        self._read_data_csv()
        self._get_data_info()
        self._filter_data()
        self._calculate_per()
        self._make_per_fold()
        self._save_data()
        self._generate_report()

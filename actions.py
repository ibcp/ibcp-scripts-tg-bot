import os
import re
import shutil
import glob
import logging
from typing import Optional, Union, Dict, Callable, List

import numpy as np
import pandas as pd
import pyspectra


def load_ratio_files(
    ccode: Optional[str] = None,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Read ratio files

    By default, all ratio files are read and the output is a dict <ccode>:
    <DataFrame of the ratio coefficients>.  If `ccode` is provided,
    then only the corresponding DataFrame is returned. I.e. the output is
    equivalent to load_ratio_files()[ccode]
    """
    from app import app

    RATIO_FILES_DIR = app.config["RATIO_FILES_DIR"]
    if ccode is not None:
        ratio_file = os.path.join(RATIO_FILES_DIR, f"{ccode.upper()}.txt")
        return pd.read_csv(
            ratio_file, header=None, sep=";", names=["Pixel", "Coeff"]
        )

    ratios = {}
    for ratio_file in glob.glob(
        os.path.join(RATIO_FILES_DIR, "*.txt"), recursive=False
    ):
        ccode = os.path.basename(ratio_file).split(".")[0]
        df = pd.read_csv(
            ratio_file, header=None, sep=";", names=["Pixel", "Coeff"]
        )
        df["Pixel"] = df["Pixel"].astype(np.uint16)
        ratios[ccode] = df
    return ratios


def read_bwtek_with_ratio_correction(filepath: str) -> pyspectra.Spectra:
    """Read BWTek files with custom ratio files"""
    # Find a row where the data starts
    ccode = None
    with open(filepath, "r") as fp:
        line = fp.readline()
        cnt = 0
        if not line.startswith("File Version;BWSpec"):
            raise TypeError(
                "Incorrect BWTek file format. The first row does "
                "not match 'File Version;BWSpec<...>'"
            )

        while line and not line.startswith("Pixel;"):
            line = fp.readline()
            if line.startswith("c code;"):
                ccode = line.split(";")[1].strip()
            cnt += 1

        # Check that 'c code' and 'Pixel' values were found
        if ccode is None:
            raise TypeError(
                "Incorrect BWTek file format. 'c code' value was not found"
            )
        if not line.startswith("Pixel;"):
            raise TypeError(
                "Incorrect BWTek file format. Could not to find a "
                "row starting with 'Pixel;'"
            )
        # Get decimal delimiter
        first_data_line = fp.readline().strip()
        decimal_del = re.sub("[0-9; -]", "", first_data_line)
        decimal_del = list(set(list(decimal_del)))
        if not (len(decimal_del) == 1 and decimal_del[0] in (",", ".")):
            raise TypeError(
                "Incorrect BWTek file format. Could not to find the decimal delimiter"
            )
        decimal_del = decimal_del[0]

    # CSV read options
    options = {
        "skiprows": cnt,
        "sep": ";",
        "decimal": decimal_del,
        "na_values": ("", " ", "  ", "   ", "    "),
        "usecols": [
            "Pixel",
            "Raman Shift",
            "Dark",
            "Raw data #1",
            "Dark Subtracted #1",
        ],
        "dtype": np.float64,
    }
    data = pd.read_csv(filepath, **options)
    data["raw_without_dark"] = data["Raw data #1"] - data["Dark"]

    # Load corresponding ratio coefficients
    ratio = load_ratio_files(ccode)

    if data.shape[0] != ratio.shape[0]:
        raise TypeError(
            "The spectrum file and the corresponding ratio file have different number of rows"
        )

    # Apply the coefficients. To be sure, join data and ratio coefficients by Pixel value
    data["Pixel"] = data["Pixel"].astype(ratio["Pixel"].dtype)
    ratio.set_index("Pixel", inplace=True)
    data.set_index("Pixel", inplace=True)
    data = pd.concat([data, ratio], axis=1)
    data["corrected_raw_without_dark"] = (
        data["raw_without_dark"] * data["Coeff"]
    )

    # Clear values before writing to the file
    data = data[["Raman Shift", "corrected_raw_without_dark"]]
    data.dropna(axis=0, how="any", inplace=True)

    s = pyspectra.Spectra(
        spc=data["corrected_raw_without_dark"],
        wl=data["Raman Shift"],
        data={"ccode": ccode},
        keep_indexes=False,
    )
    s.reset_index(drop=True, inplace=True)
    return s


def transform_bwtek_single_file(
    filepath: str, recalibrate: bool = False
) -> None:
    """Transform a single BWTek-file (with replacement) to a two-columns *.txt file"""
    if recalibrate:
        spc = read_bwtek_with_ratio_correction(filepath)
    else:
        spc = pyspectra.read_bwtek(filepath)
    spc = spc[:, :, 80:3010]
    df = pd.DataFrame({"wl": spc.wl, "spc": spc.spc.iloc[0, :].values})
    df.to_csv(filepath, header=False, index=False)


def transform_files(
    files: List[str], callback: Callable, **kwargs
) -> Dict[str, bool]:
    """ Call a callback function for each file in a file list"""
    files_status = {}
    for filename in files:
        if os.path.isfile(filename):
            try:
                callback(filename, **kwargs)
                files_status[filename] = True
            except Exception as e:
                files_status[filename] = False
                logging.error(e)
    return files_status


def transform_bwtek(target_dir: str) -> Dict[str, bool]:
    files = glob.iglob(os.path.join(target_dir, "**/*.txt"), recursive=True)
    return transform_files(files, transform_bwtek_single_file)


def recalibrate_bwtek(target_dir: str) -> Dict[str, bool]:
    files = glob.iglob(os.path.join(target_dir, "**/*.txt"), recursive=True)
    return transform_files(
        files, transform_bwtek_single_file, recalibrate=True
    )


def dep(target_dir: str) -> Dict[str, bool]:
    """Build summary of a dielectrophoresis experiment"""

    # If all in one root dir switch to it
    content = os.listdir(target_dir)
    if (len(content) == 1) and (
        os.path.isdir(os.path.join(target_dir, content[0]))
    ):
        target_dir = os.path.join(target_dir, content[0])

    # Read all files
    files = glob.glob(os.path.join(target_dir, "**/*.txt"), recursive=True)
    s = pyspectra.read_filelist(
        files, read_bwtek_with_ratio_correction, meta="Date"
    )
    s.reset_index(drop=True, inplace=True)
    df = s.data
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d %H:%M:%S")

    # Folder of the file
    df["folder"] = (
        df["filename"]
        .apply(os.path.dirname)
        .str.slice(start=len(target_dir))
        .str.lstrip(os.path.sep)
        .astype("category")
    )

    # Experiment is the first folder of the file
    df["experiment"] = (
        df["folder"]
        .astype("str")
        .apply(lambda x: x.split(os.path.sep)[0])
        .astype("category")
    )

    # Remove folder from filename (this also uses less memory)
    df["filename"] = df["filename"].apply(os.path.basename)

    # Calculate relative time
    start_time = df.groupby("experiment")["Date"].min()
    df["start_time"] = start_time[df.experiment.values].values
    df["relative_time, sec"] = (
        (df["Date"] - df["start_time"]).dt.total_seconds().astype(np.uint16)
    )

    # Calculate relative peak intensity
    spc = s[:, :, 1500:1651]
    bl = spc.copy()
    bl.spc.iloc[:, 1:-1] = np.nan
    bl.approx_na(inplace=True, method="linear")
    df["relative_peak"] = (spc - bl).spc.max(axis=1).values.round(1)

    # Clear target dir to keep only reports
    shutil.rmtree(target_dir, ignore_errors=True)
    os.mkdir(target_dir)

    # Write to excel
    df.sort_values(by=["experiment", "Date"], inplace=True)
    df.rename(columns={"Date": "datetime"}, inplace=True)
    columns = [
        "folder",
        "filename",
        "datetime",
        "relative_time, sec",
        "relative_peak",
    ]
    with pd.ExcelWriter(
        os.path.join(target_dir, "report.xlsx"), engine="openpyxl"
    ) as writer:
        for experiment in df["experiment"].cat.categories:
            df.loc[df["experiment"] == experiment, columns].to_excel(
                writer, sheet_name=experiment, header=True, index=False
            )
            writer.sheets[experiment].column_dimensions["A"].width = (
                df.loc[df["experiment"] == experiment, "folder"]
                .str.len()
                .max()
                + 2
            )
            writer.sheets[experiment].column_dimensions["B"].width = 20
            writer.sheets[experiment].column_dimensions["C"].width = 20
            writer.sheets[experiment].column_dimensions["D"].width = 20
            writer.sheets[experiment].column_dimensions["E"].width = 15
    return {"report.xlsx": True}


def process_agnp_synthesis_experiments(target_dir: str) -> Dict[str, bool]:
    """Build summary of an AgNp synthesis experiment"""
    # Read all files
    files = glob.glob(os.path.join(target_dir, "**/*.txt"), recursive=True)
    s = pyspectra.read_filelist(files, read_bwtek_with_ratio_correction)
    s.reset_index(drop=True, inplace=True)
    df = s.data

    # Keep only used region to use less memory
    df["peak_mPBA"] = (
        # Peak - background
        s[:, :, 1560:1590].spc.max(axis=1)
        - s[:, :, 1610:1630].spc.median(axis=1)
    )
    df["peak_xanth"] = (
        # Peak - background
        s[:, :, 630:680].spc.max(axis=1)
        - s[:, :, 1990:2010].spc.median(axis=1)
    )
    df["peak_amPyr"] = (
        # Peak - background. Dummy values, for now
        s[:, :, 1990:2010].spc.max(axis=1)
        - s[:, :, 1990:2010].spc.max(axis=1)
    )
    del s

    # Folder of the file
    df["folder"] = (
        df["filename"]
        .apply(lambda x: x.split(os.path.sep)[-2])
        .astype("category")
    )
    df["filename"] = df["filename"].apply(os.path.basename)

    # Sort and fill missing values
    df["sp"] = (
        df["filename"].str.extract(r"^SP_([0-9]+)[ \.]").astype(np.uint16)
    )
    df.sort_values(["folder", "sp"], inplace=True)
    df[["analyte", "concentration", "synthesis"]] = df["filename"].str.extract(
        r"^SP_[0-9]+ ([a-zA-Z0-9_]+) ([0-9_]+) AgNP (N[1-9]+)\.txt$"
    )
    df.fillna(method="ffill", inplace=True)

    # Format fields
    df["concentration"] = (
        df["concentration"]
        .str.replace("_", ".", regex=False)
        .astype(np.float32)
    )
    df["synthesis"] = df["synthesis"].astype("category")
    df["peak"] = (
        df["peak_mPBA"] * df["analyte"].isin(["NaAc", "mPBA"]).astype(np.uint8)
        + df["peak_xanth"]
        * df["analyte"].isin(["NaAc_x", "xanth"]).astype(np.uint8)
        + df["peak_amPyr"]
        * df["analyte"].isin(["NaAc_ap", "amPyr"]).astype(np.uint8)
    )

    # Build the pivot
    df["repetition"] = (
        df.groupby(["folder", "synthesis", "concentration"])["sp"]
        .rank(method="first", ascending=True)
        .astype(np.uint8)
    )
    df["sr"] = df["synthesis"].astype(str) + "_" + df["repetition"].astype(str)
    res = df.pivot_table(
        values="peak", index=["folder", "concentration"], columns=["sr"]
    ).reset_index()
    res["avg"] = res.iloc[:, 2:].mean(axis=1)

    # Clear target dir to keep only reports
    shutil.rmtree(target_dir, ignore_errors=True)
    os.mkdir(target_dir)

    # Write to Excel file
    with pd.ExcelWriter(
        os.path.join(target_dir, "peak_values.xlsx"), engine="openpyxl"
    ) as writer:
        for folder in df["folder"].cat.categories:
            res.loc[df["folder"] == folder, res.columns != "folder"].to_excel(
                writer, sheet_name=folder, header=True, index=False
            )
    return {"peak_values.xlsx": True}

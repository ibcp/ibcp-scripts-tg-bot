import os
import shutil
import glob
import logging
import numpy as np
import pandas as pd
import pyspectra


def recalibrate_single_file(filepath):
    """Recalibrate single file with replacement"""
    spc = pyspectra.read_bwtek(filepath)
    spc = spc[:, :, 80:3010]
    df = pd.DataFrame({"wl": spc.wl, "spc": spc.spc.iloc[0, :].values})
    df.to_csv(filepath, header=False, index=False)


def recalibrate(target_dir):
    files_status = {}
    for filename in glob.iglob(
        os.path.join(target_dir, "**/*.txt"), recursive=True
    ):
        if os.path.isfile(filename):
            try:
                recalibrate_single_file(filename)
                files_status[filename] = True
            except Exception as e:
                files_status[filename] = False
                logging.error(e)
    return files_status


def dep(target_dir):
    """Build summary of a dielectrophoresis experiment"""

    # If all in one root dir switch to it
    content = os.listdir(target_dir)
    if (len(content) == 1) and (
        os.path.isdir(os.path.join(target_dir, content[0]))
    ):
        target_dir = os.path.join(target_dir, content[0])

    # Read all files
    files = glob.glob(os.path.join(target_dir, "**/*.txt"), recursive=True)
    s = pyspectra.read_filelist(files, pyspectra.read_bwtek, meta="Date")
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


def process_agnp_synthesis_experiments(target_dir):
    """Build summary of an AgNp synthesis experiment"""
    # Read all files
    files = glob.glob(os.path.join(target_dir, "**/*.txt"), recursive=True)
    s = pyspectra.read_filelist(files, pyspectra.read_bwtek)
    s.reset_index(drop=True, inplace=True)
    df = s.data
    # Keep only used region to use less memory
    df["peak"] = s[:, :, 1560:1590].spc.max(axis=1)
    df["bg"] = s[:, :, 1990:2010].spc.median(axis=1)
    df["peak_rel"] = df["peak"] - df["bg"]
    del s

    # Folder of the file
    df["folder"] = (
        df["filename"]
        .apply(lambda x: x.split(os.path.sep)[-2])
        .astype("category")
    )
    df["filename"] = df["filename"].apply(os.path.basename)
    df["sp"] = (
        df["filename"].str.extract(r"^SP_([0-9]+)[ \.]").astype(np.uint16)
    )
    df.sort_values("sp", inplace=True)
    df[["concentration", "synthesis"]] = df["filename"].str.extract(
        r"^SP_[0-9]+ [a-zA-Z0-9]+ ([0-9]+) AgNP (N[1-9]+)\.txt$"
    )
    df.fillna(method="ffill", inplace=True)
    df["concentration"] = df["concentration"].astype(np.uint16)
    df["synthesis"] = df["synthesis"].astype("category")
    df["repetition"] = (
        df.groupby(["synthesis", "concentration"])["sp"]
        .rank(method="first", ascending=True)
        .astype(np.uint8)
    )
    df["sr"] = df["synthesis"].astype(str) + "_" + df["repetition"].astype(str)
    res = df.pivot_table(
        values="peak_rel", index=["folder", "concentration"], columns=["sr"]
    ).reset_index()
    res["avg"] = res.iloc[:, 2:].mean(axis=1)

    with pd.ExcelWriter(
        os.path.join(target_dir, "peak_values.xlsx"), engine="openpyxl"
    ) as writer:
        for folder in df["folder"].cat.categories:
            res.loc[df["folder"] == folder, res.columns != "folder"].to_excel(
                writer, sheet_name=folder, header=True, index=False
            )
    return {"peak_values.xlsx": True}

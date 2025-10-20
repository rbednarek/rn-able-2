import pandas as pd
import gzip


def read_csv(file_path, index_col=0):
    """Reads a CSV or TSV file into a DataFrame"""
    if file_path.endswith(".csv") or file_path.endswith(".csv.gz"):
        df = pd.read_csv(file_path, index_col=index_col)
    elif file_path.endswith(".tsv") or file_path.endswith(".tsv.gz"):
        df = pd.read_csv(file_path, sep="\t", index_col=index_col)
    else:
        raise ValueError(
            "Invalid file format. Please provide a .csv, .csv.gz, .tsv, or .tsv.gz file."
        )
    return df


def write_csv(df, file_path, index=False):
    df.to_csv(file_path, index=index)


def geo_series_matrix_to_df(
    geo_txt,
    accessions="!Sample_geo_accession",
    condition1="!Sample_source_name_ch1",
    condition2=None,
):
    with gzip.open(geo_txt, "rt") as f:
        for i in f:
            if i.startswith(accessions):
                sample_names = i.strip().split("\t")[1:]
            elif i.startswith(condition1):
                sample_condition = i.strip().split("\t")[1:]
            elif condition2 and i.startswith(condition2):
                sample_condition2 = i.strip().split("\t")[1:]
    if sample_names and sample_condition:
        df = pd.DataFrame({"sample": sample_names, "condition": sample_condition})
        df.applymap(lambda x: x.replace('"', "") if isinstance(x, str) else x)
        df.set_index("sample", inplace=True)
        if condition2 and sample_condition2:
            df["condition2"] = sample_condition2
        return df
    else:
        raise ValueError(
            "Could not find the specified accessions or condition in the file."
        )
        return None

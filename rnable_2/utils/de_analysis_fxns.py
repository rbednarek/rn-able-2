from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import pandas as pd
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri, default_converter
from rpy2.robjects.conversion import localconverter


def plot_count_pca(
    count_df,
    raw_count=10,
    min_samples=3,
    components=2,
    log=True,
    plot=True,
    meta_df=None,
    col1=None,
    col2=None,
    exp=None,
):
    """Perform PCA on count data and plot the results.
    Inputs:
    - count_df: Raw count DataFrame
    - raw_count: Gene must have minimum count of raw_count in at least (min_samples) to be considered when calculating PCA
    - min_samples: Minimum number of samples a gene must be expressed in at (raw_count levels) to be considered
    - log: Whether to log-transform the data
    - plot: Whether to plot the PCA results
    - meta_df: Optional metadata DataFrame for coloring points in the PCA plot (optional)
    - col1: Name of the first column in meta_df to use for coloring points - (if meta_df provided, not optional)
    - col2: Name of the second column in meta_df to use for shaping points (optional)
    - exp: name of the experiment (optional)
    Output:
    - pca_df: DataFrame with PCA results
    - pc1_variance: Variance explained by PC1
    - pc2_variance: Variance explained by PC2
    """
    pca = PCA(n_components=components)
    count_filter = count_df.loc[:, (count_df > raw_count).sum(axis=0) >= min_samples]
    if log:
        count_filter = np.log1p(count_filter)
    pca_result = pca.fit_transform(count_filter.T)
    variance = pca.explained_variance_ratio_ * 100
    pc1_variance = round(variance[0], 2)
    pc2_variance = round(variance[1], 2)

    pca_df = pd.DataFrame(
        pca_result, columns=["PC1", "PC2"], index=count_filter.columns
    )
    if meta_df is not None:
        pca_df = pca_df.join(meta_df, how="left")
    if plot:
        plt.figure(figsize=(8, 6))
        if meta_df is not None:
            markers = ["o", "s", "^", "D", "X", "P", "*"]
            if col2 and col2 in pca_df.columns:
                for (color, shape), group in pca_df.groupby([col1, col2]):
                    plt.scatter(
                        group["PC1"],
                        group["PC2"],
                        label=f"{color}-{shape}",
                        marker=markers[hash(shape) % len(markers)],
                    )
            elif col1 and col1 in pca_df.columns:
                for color, group in pca_df.groupby(col1):
                    plt.scatter(group["PC1"], group["PC2"], label=color)
        else:
            plt.scatter(pca_df["PC1"], pca_df["PC2"])
        if exp:
            plt.title(f"{exp} - Count Data PCA")
        else:
            plt.title("Count Data PCA")
        plt.xlabel(f"PC1 ({pc1_variance}%)")
        plt.ylabel(f"PC2 ({pc2_variance}%)")
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.grid()
        plt.show()
    return pca_df, pc1_variance, pc2_variance


def run_de_analysis(counts_df, meta_df, group1, group2, cat_col="group"):
    """Run differential expression analysis.
    Inputs:
    - counts_df: Raw count DataFrame with column names matching meta_df row names
    - meta_df: Sample metadata with column defining sample groups (default 'group') and row names matching counts_df column names
    - group1: Name of the first group for comparison
    - group2: Name of the second group for comparison
    - cat_col: Name of the column in meta_df that defines the sample groups (default 'group')
    Outputs:
    - res_df: DataFrame with differential expression results
    """

    meta_df[cat_col] = pd.Categorical(meta_df[cat_col], categories=[group1, group2])
    with localconverter(default_converter + pandas2ri.converter):
        r_counts_df = pandas2ri.py2rpy(counts_df)
        r_meta_df = pandas2ri.py2rpy(meta_df)
        base = importr("base")
        deseq2 = importr("DESeq2")
        dds = deseq2.DESeqDataSetFromMatrix(
            countData=r_counts_df, colData=r_meta_df, design=ro.Formula("~ group")
        )
        dds = deseq2.DESeq(dds)
        res = deseq2.results(dds)
        res_df = base.as_data_frame(res)

    return res_df

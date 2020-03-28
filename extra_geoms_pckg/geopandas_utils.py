#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

import pandas as pd


def optimize_df(df):
    """
    Retorna el pd.Dataframe optimizado segun columnas que encuentre

    Args:
        df:

    Returns:
        opt_df (pandas.Dataframe)
    """
    opt_df = df.copy()
    df_ints = opt_df.select_dtypes(include=['int64'])
    opt_df[df_ints.columns] = df_ints.apply(pd.to_numeric, downcast='signed')
    df_floats = opt_df.select_dtypes(include='float')
    opt_df[df_floats.columns] = df_floats.apply(pd.to_numeric, downcast='float')
    for col in opt_df.select_dtypes(exclude='datetime').columns:
        try:
            unic_vals = opt_df[col].unique()
        except:
            continue

        num_unique_values = len(unic_vals)
        num_total_values = len(opt_df[col])
        if num_unique_values / num_total_values < 0.5:
            opt_df.loc[:, col] = opt_df[col].astype('category')

    return opt_df

from .preprocessing import df_to_xy
from .benchmark import process_benchmark_cv
from core.models.metrics import avg_gain_ratio
from joblib import Parallel, delayed

def _ffs_step(model, df, top_columns, column, cv, ravel_target, df_to_xy_kwargs, enforced_target_values):
    current_columns = top_columns + [column]
    X, y = df_to_xy(df, select_columns=current_columns, **df_to_xy_kwargs)
    if ravel_target:
        y = y.ravel()
    tmp_res = process_benchmark_cv(model, X, y, cv=cv, enforced_target_values=enforced_target_values)
    loss = tmp_res["avg_loss_ratio"].mean()
    return loss, column

def ffs(model, df, selected_columns=None, target_column="min_offer", df_to_xy_kwargs=None, cv=3, ravel_target=True, n_jobs=-2, enforced_target_values=None, early_stop=2):
    """
    Forward feature selection
    """
    if selected_columns is None:
        selected_columns = [col for col in df.columns if col != target_column]
    if df_to_xy_kwargs is None:
        df_to_xy_kwargs = {"normalize": True, "centered": False}
    df = df[selected_columns + [target_column]]

    top_columns = []
    top_loss = float("inf")
    rounds_without_improvements = 0
    for _ in range(len(selected_columns)):
        top_column = None
        top_column_loss = float("inf")
        lst_args = [(model, df, top_columns, column, cv, ravel_target, df_to_xy_kwargs, enforced_target_values) for column in selected_columns if column not in top_columns]
        results = Parallel(n_jobs=n_jobs)(delayed(_ffs_step)(*args) for args in lst_args)
        for loss, column in results:
            if top_column is None:
                top_column = column
                top_column_loss = loss
            elif top_column_loss > loss:
                top_column = column
                top_column_loss = loss
        if top_column_loss < top_loss:
            top_loss = top_column_loss
            top_columns += [top_column]
            rounds_without_improvements = 0
        elif top_column_loss > top_loss:
            rounds_without_improvements += 1
        if early_stop <= rounds_without_improvements:
            # We won't get any better from this point. :/
            return top_columns, top_loss
    return top_columns, top_loss

def select_corr_columns(df, selected_columns=None, target_treshold=0.05, target_column="min_offer"):
    if selected_columns is None:
        selected_columns = [col for col in df.columns if col!=target_column]
    target_corr = df[selected_columns + [target_column]].corr()[target_column]
    top_corr_columns = target_corr[abs(target_corr) > target_treshold]
    return [col for col in top_corr_columns.keys() if col != target_column]


    
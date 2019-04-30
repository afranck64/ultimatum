#TODO: check later (import from models.metrics?)
MAX_GAIN = 200

def df_to_xy(df, normalize=True, centered=False, drop_columns=None, normalize_target=False):

    df_effort = df[['time_spent_prop', 'count_effort']]
    df_effort = (df_effort - df_effort.min()) / (df_effort.max() - df_effort.min())

    df['effort'] = df_effort['time_spent_prop'] * df_effort['count_effort']
    df = df[['time_spent_risk', 'cells', 'selfish', 'effort',
            'Honesty_Humility','Extraversion', 'Agreeableness', 'min_offer']]
    

    x = df.values[:, :-1]
    y = df.values[:, -1:]

    if normalize:
        x_min = x.min(axis=0)
        x_max = x.max(axis=0)
        x = (x - x_min) / (x_max - x_min)
    if centered:
        x -= x.mean()
    
    if normalize_target:
        y /= MAX_GAIN
    
    return x, y
        
"""Builds a small DuckDB database from the simulation, shaped like real event data.

Tables:
  users(user_id, tier, platform, sessions_pre, tenure_days)
  assignments(user_id, variant, enroll_date)
  purchases(purchase_id, user_id, purchase_ts, kind, amount)
      kind is 'subscription', 'subscription_renewal' or 'iap'
  hillstrom  -> the real e-mail experiment CSV, loaded as is

The event log is made up from the user-level simulation in a way that the SQL
metrics give back exactly the same numbers as the Python ones. The timestamps
inside each window are random, only the windows matter.
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .simulator import SimConfig, simulate

BASE_DATE = pd.Timestamp("2026-01-01")


def _events(df, cfg, rng):
    price = np.where(df.treatment == 1, cfg.price_variant, cfg.price_control)
    enroll = BASE_DATE + pd.to_timedelta(df.enroll_day.to_numpy(), unit="D")
    ids = df.user_id.to_numpy()
    parts = []

    # subscription starts somewhere in the 14-day conversion window
    m = df.converted.to_numpy() == 1
    sub_ts = enroll[m] + pd.to_timedelta(rng.uniform(0, 13.99, m.sum()), unit="D")
    parts.append(pd.DataFrame({"user_id": ids[m], "purchase_ts": sub_ts,
                               "kind": "subscription", "amount": price[m]}))

    # renewal exactly 30 days later, for the payers who stayed
    r = df.retained_m2.to_numpy() == 1
    sub_ts_all = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    sub_ts_all[m] = sub_ts
    parts.append(pd.DataFrame({"user_id": ids[r],
                               "purchase_ts": sub_ts_all[r].to_numpy() + np.timedelta64(30, "D"),
                               "kind": "subscription_renewal", "amount": price[r]}))

    # in-app spend in the first 30 days (one event per user is enough here)
    iap = df.revenue_30d.to_numpy() - price * df.converted.to_numpy()
    k = iap > 1e-9
    parts.append(pd.DataFrame({"user_id": ids[k],
                               "purchase_ts": enroll[k] + pd.to_timedelta(rng.uniform(0, 29.99, k.sum()), unit="D"),
                               "kind": "iap", "amount": iap[k]}))

    # spend in the 30 days before enrollment (the CUPED covariate)
    pre = df.revenue_pre_30d.to_numpy() > 0
    parts.append(pd.DataFrame({"user_id": ids[pre],
                               "purchase_ts": enroll[pre] - pd.to_timedelta(rng.uniform(0.01, 30, pre.sum()), unit="D"),
                               "kind": "iap", "amount": df.revenue_pre_30d.to_numpy()[pre]}))

    ev = pd.concat(parts, ignore_index=True).sort_values(["purchase_ts", "user_id"]).reset_index(drop=True)
    ev.insert(0, "purchase_id", np.arange(len(ev)))
    return ev


def build_warehouse(db_path, cfg=None, hillstrom_csv=None, seed=123):
    """(Re)create the DuckDB file. Returns the user-level simulation so you can cross-check."""
    cfg = cfg or SimConfig()
    df = simulate(cfg)
    rng = np.random.default_rng(seed)

    users = df[["user_id", "tier", "platform", "sessions_pre", "tenure_days"]]
    assignments = pd.DataFrame({
        "user_id": df.user_id,
        "variant": np.where(df.treatment == 1, "treatment", "control"),
        "enroll_date": (BASE_DATE + pd.to_timedelta(df.enroll_day, unit="D")).dt.date,
    })
    purchases = _events(df, cfg, rng)

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    for name, frame in [("users", users), ("assignments", assignments), ("purchases", purchases)]:
        con.register("tmp_df", frame)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    con.execute("ALTER TABLE assignments ALTER enroll_date TYPE DATE")
    if hillstrom_csv is not None and Path(hillstrom_csv).exists():
        con.execute("CREATE TABLE hillstrom AS SELECT * FROM read_csv_auto(?)", [str(hillstrom_csv)])
    con.close()
    return df


def run_file(con, path):
    """Run a .sql file statement by statement and return the last result as a DataFrame."""
    # drop comment lines first so a ';' inside a comment can't split a statement
    sql = "\n".join(line for line in Path(path).read_text().splitlines() if not line.strip().startswith("--"))
    out = None
    for statement in sql.split(";"):
        if statement.strip():
            out = con.execute(statement).df()
    return out

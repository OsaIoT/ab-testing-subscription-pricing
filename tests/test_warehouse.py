import duckdb
import numpy as np
import pytest

from src import analysis as an
from src.simulator import SimConfig
from src.warehouse import build_warehouse, run_file

SQL = "sql"


@pytest.fixture(scope="module")
def wh(tmp_path_factory):
    path = tmp_path_factory.mktemp("wh") / "w.duckdb"
    df = build_warehouse(path, SimConfig(n_users=8_000, seed=21))
    con = duckdb.connect(str(path))
    run_file(con, f"{SQL}/03_user_metrics_view.sql")
    yield con, df
    con.close()


def test_sql_user_metrics_match_python_exactly(wh):
    con, df = wh
    m = con.execute("SELECT * FROM user_metrics ORDER BY user_id").df()
    d = df.sort_values("user_id").reset_index(drop=True)
    for col in ["converted", "retained_m2", "revenue_30d", "revenue_60d", "revenue_pre_30d"]:
        assert np.allclose(m[col].to_numpy(float), d[col].to_numpy(float), atol=1e-8), col
    assert len(m) == len(d)  # the join must not drop anyone


def test_sql_effect_equals_python_effect(wh):
    con, df = wh
    sql = run_file(con, f"{SQL}/04_effect_estimate.sql").iloc[0]
    py = an.diff_in_means(df.revenue_30d.to_numpy(), df.treatment.to_numpy())
    assert sql["diff"] == pytest.approx(py.estimate) and sql["se"] == pytest.approx(py.se)


def test_sql_cuped_equals_python_cuped(wh):
    con, df = wh
    sql = run_file(con, f"{SQL}/05_cuped.sql").iloc[0]
    py, vr = an.cuped_effect(df.revenue_30d.to_numpy(), df.revenue_pre_30d.to_numpy(), df.treatment.to_numpy())
    assert sql["diff_cuped"] == pytest.approx(py.estimate, abs=1e-9) and sql["variance_reduction"] == pytest.approx(vr)


def test_health_checks_clean_and_inner_join_pitfall_is_biased(wh):
    con, df = wh
    assert len(run_file(con, f"{SQL}/02_contamination_check.sql")) == 0
    pit = run_file(con, f"{SQL}/09_pitfall_inner_join.sql")
    assert (pit.arpu_inner_join > pit.arpu_all_exposed_users).all()

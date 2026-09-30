from scoring.data import load_pipeline, split_pipeline


def test_nenhuma_linha_perdida_no_merge():
    df = load_pipeline()
    assert len(df) == 8800
    assert df["opportunity_id"].is_unique


def test_nomes_normalizados():
    df = load_pipeline()
    assert "GTXPro" not in set(df["product"])
    assert "technolgy" not in set(df["sector"].dropna())
    assert df["sales_price"].notna().all()


def test_separacao_entre_abertos_e_fechados():
    closed, open_ = split_pipeline(load_pipeline())
    assert len(open_) == 2089
    assert set(open_["deal_stage"]) == {"Prospecting", "Engaging"}
    assert set(closed["deal_stage"]) == {"Won", "Lost"}
    assert closed["won"].isin([0, 1]).all()


def test_idade_so_para_engaging_aberto():
    closed, open_ = split_pipeline(load_pipeline())
    assert closed["age_days"].isna().all()
    engaging = open_[open_["deal_stage"] == "Engaging"]
    prospecting = open_[open_["deal_stage"] == "Prospecting"]
    assert engaging["age_days"].notna().all()
    assert prospecting["age_days"].isna().all()
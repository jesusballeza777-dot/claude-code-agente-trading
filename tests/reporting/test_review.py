"""Fichas de aprendizaje: etiquetas deterministas y su impacto agregado."""

from decimal import Decimal

from factories import make_trade, r_trade
from trading.audit import ExitReason
from trading.reporting import ReviewTag, review_trade, tag_impact

T = ReviewTag
MODEL_BPS = Decimal(5)


def test_clean_winner() -> None:
    review = review_trade(make_trade(), MODEL_BPS)
    assert review.tags == (T.GANADORA,)
    assert review.r_multiple == make_trade().r_multiple


def test_clean_stop() -> None:
    review = review_trade(r_trade("s", -1, 1, exit_reason=ExitReason.STOP), MODEL_BPS)
    assert review.tags == (T.PERDEDORA, T.STOP_LIMPIO)


def test_loss_beyond_one_r_by_gap() -> None:
    review = review_trade(r_trade("g", Decimal("-1.5"), 1, exit_reason=ExitReason.STOP), MODEL_BPS)
    assert T.PERDIDA_MAYOR_QUE_R in review.tags
    assert T.STOP_LIMPIO not in review.tags


def test_slippage_above_model() -> None:
    review = review_trade(make_trade(entry_price=Decimal(60060)), MODEL_BPS)  # 10 pb
    assert T.SLIPPAGE_SOBRE_MODELO in review.tags
    assert review.entry_slippage_bps == Decimal(10)


def test_relevant_funding() -> None:
    assert T.FUNDING_RELEVANTE in review_trade(make_trade(funding=Decimal("1.3")), MODEL_BPS).tags
    assert T.FUNDING_RELEVANTE not in review_trade(make_trade(), MODEL_BPS).tags
    flat = make_trade(exit_price=Decimal(60000), expected_exit_price=Decimal(60000))
    assert T.FUNDING_RELEVANTE not in review_trade(flat, MODEL_BPS).tags  # bruto 0


def test_profit_given_back() -> None:
    trade = r_trade("v", Decimal("-0.2"), 1, max_favorable_price=Decimal(120))  # llegó a +2 R
    review = review_trade(trade, MODEL_BPS)
    assert T.GANANCIA_DEVUELTA in review.tags
    assert review.mfe_r == Decimal(2)


def test_tag_impact_shows_where_money_is_lost() -> None:
    reviews = [
        review_trade(r_trade("a", -1, 1, exit_reason=ExitReason.STOP), MODEL_BPS),
        review_trade(r_trade("b", Decimal("-1.5"), 2, exit_reason=ExitReason.STOP), MODEL_BPS),
        review_trade(r_trade("c", 2, 3), MODEL_BPS),
    ]
    impact = tag_impact(reviews)
    assert impact[T.PERDEDORA].count == 2
    assert impact[T.PERDEDORA].total_r == Decimal("-2.5")
    assert impact[T.PERDIDA_MAYOR_QUE_R].total_r == Decimal("-1.5")
    assert impact[T.GANADORA].total_r == 2
    assert T.FUNDING_RELEVANTE not in impact


def test_breakeven_has_no_result_tag() -> None:
    review = review_trade(r_trade("z", 0, 1), MODEL_BPS)
    assert review.tags == ()

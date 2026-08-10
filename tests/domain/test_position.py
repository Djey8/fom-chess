from chess.domain.position import Position


def test_from_algebraic_roundtrip():
    for sq in ("a1", "h1", "a8", "h8", "e4", "d5"):
        assert Position.from_algebraic(sq).algebraic == sq


def test_a1_is_bottom_left():
    p = Position.from_algebraic("a1")
    assert (p.row, p.col) == (7, 0)


def test_h8_is_top_right():
    p = Position.from_algebraic("h8")
    assert (p.row, p.col) == (0, 7)


def test_offset_bounds():
    assert Position.from_algebraic("a1").offset(0, -1) is None
    assert Position.from_algebraic("h8").offset(-1, 1) is None
    assert Position.from_algebraic("e4").offset(-1, 0).algebraic == "e5"

from trusted_ui.table_refresh import task_table_interval, visible_rows_signature


def test_visible_rows_signature_is_stable_and_tracks_visible_values() -> None:
    assert visible_rows_signature((("a", 1),)) == (("a", "1"),)
    assert visible_rows_signature((("a", 2),)) != visible_rows_signature((("a", 1),))


def test_task_table_interval_adapts_to_activity_and_visibility() -> None:
    assert task_table_interval(active=True, visible=True) == 500
    assert task_table_interval(active=False, visible=True) == 1500
    assert task_table_interval(active=True, visible=False) == 2500

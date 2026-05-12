from nsp.formatters.plain import render as render_plain


def test_plain_lists_allocated_then_remaining(sample_result):
    out = render_plain(sample_result)
    lines = out.splitlines()
    assert lines == [
        "10.10.0.0/19",
        "10.10.32.0/20",
        "10.10.48.0/21",
        "10.10.56.0/21",
        "10.10.64.0/18",
        "10.10.128.0/17",
    ]

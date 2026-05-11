from nsp.errors import (
    NSPError,
    InvalidCIDRError,
    InvalidRequestError,
    SubnetTooLargeError,
    CapacityExceededError,
)


def test_all_errors_inherit_nsperror():
    for cls in (InvalidCIDRError, InvalidRequestError, SubnetTooLargeError, CapacityExceededError):
        assert issubclass(cls, NSPError)


def test_exit_code_is_one():
    e = InvalidCIDRError("bad")
    assert e.exit_code == 1


def test_invalid_cidr_message():
    e = InvalidCIDRError("not-a-cidr")
    msg = str(e)
    assert "invalid CIDR 'not-a-cidr'" in msg
    assert "a.b.c.d/N" in msg


def test_invalid_request_message():
    e = InvalidRequestError("web!=/19", "labels must match [A-Za-z0-9_-]+")
    msg = str(e)
    assert "web!=/19" in msg
    assert "[A-Za-z0-9_-]+" in msg


def test_subnet_too_large_message():
    e = SubnetTooLargeError(request_prefix=23, parent_cidr="10.10.0.0/24")
    msg = str(e)
    assert "/23" in msg
    assert "10.10.0.0/24" in msg
    assert ">= 24" in msg


def test_capacity_exceeded_pre_check_message():
    e = CapacityExceededError(short_by=128, requested=384, available=256)
    msg = str(e)
    assert "384" in msg and "256" in msg
    assert "128" in msg


def test_capacity_exceeded_alignment_message():
    e = CapacityExceededError(short_by=24, hint="try --sort to pack tightly",
                              align_at="10.10.8.0", align_prefix=19)
    msg = str(e)
    assert "alignment" in msg.lower()
    assert "10.10.8.0" in msg
    assert "/19" in msg
    assert "try --sort" in msg

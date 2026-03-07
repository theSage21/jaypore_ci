"""Tests for app.py — runnable with pytest."""

from app import add, greet


def test_add():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, 1) == 0


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_name():
    assert greet("CI") == "Hello, CI!"

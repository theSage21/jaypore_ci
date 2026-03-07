package main

import "testing"

func TestAdd(t *testing.T) {
	if got := Add(2, 3); got != 5 {
		t.Errorf("Add(2, 3) = %d; want 5", got)
	}
}

func TestAddNegative(t *testing.T) {
	if got := Add(-1, 1); got != 0 {
		t.Errorf("Add(-1, 1) = %d; want 0", got)
	}
}

func TestGreetDefault(t *testing.T) {
	if got := Greet(""); got != "Hello, world!" {
		t.Errorf("Greet(\"\") = %q; want \"Hello, world!\"", got)
	}
}

func TestGreetName(t *testing.T) {
	if got := Greet("CI"); got != "Hello, CI!" {
		t.Errorf("Greet(\"CI\") = %q; want \"Hello, CI!\"", got)
	}
}

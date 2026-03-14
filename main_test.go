package main

import "testing"

func TestHelloWorld(t *testing.T) {
	got := helloWorld()
	want := "hello world"
	if got != want {
		t.Errorf("helloWorld() = %q, want %q", got, want)
	}
}

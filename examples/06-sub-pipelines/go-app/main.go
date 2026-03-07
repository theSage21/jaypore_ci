// Package main is a tiny demo for the sub-pipeline example.
package main

import "fmt"

// Add returns the sum of a and b.
func Add(a, b int) int {
	return a + b
}

// Greet returns a greeting string.
func Greet(name string) string {
	if name == "" {
		name = "world"
	}
	return fmt.Sprintf("Hello, %s!", name)
}

func main() {
	fmt.Println(Greet(""))
}

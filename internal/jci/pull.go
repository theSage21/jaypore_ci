package jci

import (
	"fmt"
)

// Pull fetches CI results from remote
func Pull(args []string) error {
	remote := "origin"
	if len(args) > 0 {
		remote = args[0]
	}

	fmt.Printf("Fetching CI results from %s...\n", remote)

	// Fetch all refs/jci/* from remote
	_, err := git("fetch", remote, "refs/jci/*:refs/jci/*")
	if err != nil {
		fmt.Printf("Warning: %v\n", err)
	}

	// Fetch all refs/jci-runs/* from remote
	_, err = git("fetch", remote, "refs/jci-runs/*:refs/jci-runs/*")
	if err != nil {
		fmt.Printf("Warning: %v\n", err)
	}

	fmt.Println("Done")
	return nil
}

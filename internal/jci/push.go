package jci

import (
	"fmt"
)

// Push pushes CI results to remote
func Push(args []string) error {
	remote := "origin"
	if len(args) > 0 {
		remote = args[0]
	}

	refs, err := ListJCIRefs()
	if err != nil {
		return err
	}

	if len(refs) == 0 {
		fmt.Println("No CI results to push")
		return nil
	}

	fmt.Printf("Pushing %d CI result(s) to %s...\n", len(refs), remote)

	// Push all refs/jci/* to remote
	_, err = git("push", remote, "refs/jci/*:refs/jci/*")
	if err != nil {
		return err
	}

	fmt.Println("Done")
	return nil
}

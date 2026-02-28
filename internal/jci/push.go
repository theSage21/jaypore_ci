package jci

import (
	"fmt"
	"strings"
)

// Push pushes CI results to remote
func Push(args []string) error {
	remote := "origin"
	if len(args) > 0 {
		remote = args[0]
	}

	// Get all local JCI refs
	localRefs, err := ListAllJCIRefs()
	if err != nil {
		return err
	}

	if len(localRefs) == 0 {
		fmt.Println("No CI results to push")
		return nil
	}

	// Get remote refs to find what's already pushed
	remoteRefs := getRemoteJCIRefs(remote)

	// Find refs that need to be pushed
	var toPush []string
	for _, ref := range localRefs {
		if !remoteRefs[ref] {
			toPush = append(toPush, ref)
		}
	}

	if len(toPush) == 0 {
		fmt.Println("All CI results already pushed")
		return nil
	}

	fmt.Printf("Pushing %d new CI result(s) to %s...\n", len(toPush), remote)

	// Push each ref individually
	for _, ref := range toPush {
		_, err = git("push", remote, ref+":"+ref)
		if err != nil {
			return fmt.Errorf("failed to push %s: %w", ref, err)
		}
		fmt.Printf("  %s\n", ref)
	}

	fmt.Println("Done")
	return nil
}

// getRemoteJCIRefs returns a set of refs that exist on the remote
func getRemoteJCIRefs(remote string) map[string]bool {
	remoteCI := make(map[string]bool)

	// Get refs/jci/*
	out, err := git("ls-remote", "--refs", remote, "refs/jci/*")
	if err == nil && out != "" {
		for _, line := range strings.Split(out, "\n") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				remoteCI[parts[1]] = true
			}
		}
	}

	// Get refs/jci-runs/*
	out, err = git("ls-remote", "--refs", remote, "refs/jci-runs/*")
	if err == nil && out != "" {
		for _, line := range strings.Split(out, "\n") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				remoteCI[parts[1]] = true
			}
		}
	}

	return remoteCI
}

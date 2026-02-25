package main

import (
	"fmt"
	"os"

	"github.com/exedev/git-jci/internal/jci"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	var err error
	switch cmd {
	case "run":
		err = jci.Run(args)
	case "web":
		err = jci.Web(args)
	case "push":
		err = jci.Push(args)
	case "pull":
		err = jci.Pull(args)
	case "prune":
		err = jci.Prune(args)
	case "help", "-h", "--help":
		printUsage()
		return
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", cmd)
		printUsage()
		os.Exit(1)
	}

	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println(`git-jci - Local-first CI system stored in git

Usage: git jci <command> [options]

Commands:
  run     Run CI for the current commit and store results
  web     Start a web server to view CI results
  push    Push CI results to remote
  pull    Pull CI results from remote
  prune   Remove old CI results

CI results are stored in refs/jci/<commit> namespace.`)
}

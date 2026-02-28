package jci

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// git runs a git command and returns stdout
func git(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("git %s: %v\n%s", strings.Join(args, " "), err, stderr.String())
	}
	return strings.TrimSpace(stdout.String()), nil
}

// GetCurrentCommit returns the current HEAD commit hash
func GetCurrentCommit() (string, error) {
	return git("rev-parse", "HEAD")
}

// GetRepoRoot returns the root directory of the git repository
func GetRepoRoot() (string, error) {
	return git("rev-parse", "--show-toplevel")
}

// RefExists checks if a ref exists
func RefExists(ref string) bool {
	_, err := git("rev-parse", "--verify", ref)
	return err == nil
}

// StoreTree stores a directory as a tree object and creates a commit under refs/jci-runs/<commit>/<runID>
func StoreTree(dir string, commit string, message string, runID string) error {
	repoRoot, err := GetRepoRoot()
	if err != nil {
		return err
	}

	tmpIndex := repoRoot + "/.git/jci-index"
	defer exec.Command("rm", "-f", tmpIndex).Run()

	// We need to use git hash-object and mktree to build a tree
	// from files outside the repo
	treeID, err := hashDir(dir, repoRoot, tmpIndex)
	if err != nil {
		return fmt.Errorf("failed to hash directory: %w", err)
	}

	// Create commit from tree
	commitTreeCmd := exec.Command("git", "commit-tree", treeID, "-m", message)
	commitTreeCmd.Dir = repoRoot
	commitOut, err := commitTreeCmd.Output()
	if err != nil {
		return fmt.Errorf("git commit-tree: %v", err)
	}
	commitID := strings.TrimSpace(string(commitOut))

	// Update ref: refs/jci-runs/<commit>/<runid>
	ref := "refs/jci-runs/" + commit + "/" + runID
	if _, err := git("update-ref", ref, commitID); err != nil {
		return fmt.Errorf("git update-ref: %v", err)
	}

	return nil
}

// hashDir recursively hashes a directory and returns its tree ID
func hashDir(dir string, repoRoot string, tmpIndex string) (string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return "", err
	}

	var treeEntries []string

	for _, entry := range entries {
		path := filepath.Join(dir, entry.Name())

		if entry.IsDir() {
			// Recursively hash subdirectory
			subTreeID, err := hashDir(path, repoRoot, tmpIndex)
			if err != nil {
				return "", err
			}
			treeEntries = append(treeEntries, fmt.Sprintf("040000 tree %s\t%s", subTreeID, entry.Name()))
		} else {
			// Hash file
			cmd := exec.Command("git", "hash-object", "-w", path)
			cmd.Dir = repoRoot
			out, err := cmd.Output()
			if err != nil {
				return "", fmt.Errorf("hash-object %s: %v", path, err)
			}
			blobID := strings.TrimSpace(string(out))

			// Get file mode
			info, err := entry.Info()
			if err != nil {
				return "", err
			}
			mode := "100644"
			if info.Mode()&0111 != 0 {
				mode = "100755"
			}
			treeEntries = append(treeEntries, fmt.Sprintf("%s blob %s\t%s", mode, blobID, entry.Name()))
		}
	}

	// Create tree from entries
	treeInput := strings.Join(treeEntries, "\n")
	if treeInput != "" {
		treeInput += "\n"
	}

	cmd := exec.Command("git", "mktree")
	cmd.Dir = repoRoot
	cmd.Stdin = strings.NewReader(treeInput)
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("mktree: %v (input: %q)", err, treeInput)
	}

	return strings.TrimSpace(string(out)), nil
}

// ListJCIRefs returns all refs under refs/jci/
func ListJCIRefs() ([]string, error) {
	out, err := git("for-each-ref", "--format=%(refname:short)", "refs/jci/")
	if err != nil {
		return nil, err
	}
	if out == "" {
		return nil, nil
	}
	return strings.Split(out, "\n"), nil
}

// ListJCIRunRefs returns all refs under refs/jci-runs/
func ListJCIRunRefs() ([]string, error) {
	out, err := git("for-each-ref", "--format=%(refname)", "refs/jci-runs/")
	if err != nil {
		return nil, err
	}
	if out == "" {
		return nil, nil
	}
	return strings.Split(out, "\n"), nil
}

// ListAllJCIRefs returns all JCI refs (both single and multi-run)
func ListAllJCIRefs() ([]string, error) {
	var allRefs []string

	// Get refs/jci/*
	out, err := git("for-each-ref", "--format=%(refname)", "refs/jci/")
	if err == nil && out != "" {
		allRefs = append(allRefs, strings.Split(out, "\n")...)
	}

	// Get refs/jci-runs/*
	out, err = git("for-each-ref", "--format=%(refname)", "refs/jci-runs/")
	if err == nil && out != "" {
		allRefs = append(allRefs, strings.Split(out, "\n")...)
	}

	return allRefs, nil
}

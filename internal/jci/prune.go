package jci

import (
	"fmt"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// PruneOptions holds the options for the prune command
type PruneOptions struct {
	Commit    bool
	OnRemote  string
	OlderThan time.Duration
}

// ParsePruneArgs parses command line arguments for prune
func ParsePruneArgs(args []string) (*PruneOptions, error) {
	opts := &PruneOptions{}

	for _, arg := range args {
		if arg == "--commit" {
			opts.Commit = true
		} else if strings.HasPrefix(arg, "--on-remote=") {
			opts.OnRemote = strings.TrimPrefix(arg, "--on-remote=")
		} else if strings.HasPrefix(arg, "--on-remote") {
			// Handle --on-remote origin (space separated)
			continue
		} else if strings.HasPrefix(arg, "--older-than=") {
			durStr := strings.TrimPrefix(arg, "--older-than=")
			dur, err := parseDuration(durStr)
			if err != nil {
				return nil, fmt.Errorf("invalid duration %q: %v", durStr, err)
			}
			opts.OlderThan = dur
		} else if !strings.HasPrefix(arg, "-") && opts.OnRemote == "" {
			// Check if previous arg was --on-remote
			for i, a := range args {
				if a == "--on-remote" && i+1 < len(args) && args[i+1] == arg {
					opts.OnRemote = arg
					break
				}
			}
		}
	}

	return opts, nil
}

// parseDuration parses duration strings like "30d", "2w", "1h"
func parseDuration(s string) (time.Duration, error) {
	re := regexp.MustCompile(`^(\d+)([dhwm])$`)
	matches := re.FindStringSubmatch(s)
	if matches == nil {
		// Try standard Go duration
		return time.ParseDuration(s)
	}

	num, _ := strconv.Atoi(matches[1])
	unit := matches[2]

	switch unit {
	case "d":
		return time.Duration(num) * 24 * time.Hour, nil
	case "w":
		return time.Duration(num) * 7 * 24 * time.Hour, nil
	case "m":
		return time.Duration(num) * 30 * 24 * time.Hour, nil
	case "h":
		return time.Duration(num) * time.Hour, nil
	}

	return 0, fmt.Errorf("unknown unit: %s", unit)
}

// RefInfo holds information about a JCI ref
type RefInfo struct {
	Ref       string
	Commit    string
	Timestamp time.Time
	Size      int64
}

// Prune removes CI results based on options
func Prune(args []string) error {
	opts, err := ParsePruneArgs(args)
	if err != nil {
		return err
	}

	if opts.OnRemote != "" {
		return pruneRemote(opts)
	}
	return pruneLocal(opts)
}

func pruneLocal(opts *PruneOptions) error {
	refs, err := ListJCIRefs()
	if err != nil {
		return err
	}

	if len(refs) == 0 {
		fmt.Println("No CI results to prune")
		return nil
	}

	// Get info for all refs
	var refInfos []RefInfo
	var totalSize int64

	fmt.Println("Scanning CI results...")
	for i, ref := range refs {
		commit := strings.TrimPrefix(ref, "jci/")
		printProgress(i+1, len(refs), "Scanning")

		info := RefInfo{
			Ref:    ref,
			Commit: commit,
		}

		// Get timestamp from the JCI commit
		timeStr, err := git("log", "-1", "--format=%ci", "refs/jci/"+commit)
		if err == nil {
			info.Timestamp, _ = time.Parse("2006-01-02 15:04:05 -0700", timeStr)
		}

		// Get size of the tree
		info.Size = getRefSize("refs/jci/" + commit)
		totalSize += info.Size

		refInfos = append(refInfos, info)
	}
	fmt.Println() // newline after progress

	// Filter refs to prune
	var toPrune []RefInfo
	var prunedSize int64
	now := time.Now()

	for _, info := range refInfos {
		shouldPrune := false

		// Check if commit still exists (original behavior)
		_, err := git("cat-file", "-t", info.Commit)
		if err != nil {
			shouldPrune = true
		}

		// Check age if --older-than specified
		if opts.OlderThan > 0 && !info.Timestamp.IsZero() {
			age := now.Sub(info.Timestamp)
			if age > opts.OlderThan {
				shouldPrune = true
			}
		}

		if shouldPrune {
			toPrune = append(toPrune, info)
			prunedSize += info.Size
		}
	}

	if len(toPrune) == 0 {
		fmt.Println("Nothing to prune")
		fmt.Printf("Total CI data: %s\n", formatSize(totalSize))
		return nil
	}

	// Show what will be pruned
	fmt.Printf("\nFound %d ref(s) to prune:\n", len(toPrune))
	for _, info := range toPrune {
		age := ""
		if !info.Timestamp.IsZero() {
			age = fmt.Sprintf(" (age: %s)", formatAge(now.Sub(info.Timestamp)))
		}
		fmt.Printf("  %s %s%s\n", info.Commit[:12], formatSize(info.Size), age)
	}

	fmt.Printf("\nTotal to free: %s (of %s total)\n", formatSize(prunedSize), formatSize(totalSize))

	if !opts.Commit {
		fmt.Println("\n[DRY RUN] Use --commit to actually delete")
		return nil
	}

	// Actually delete
	fmt.Println("\nDeleting...")
	deleted := 0
	for i, info := range toPrune {
		printProgress(i+1, len(toPrune), "Deleting")
		if _, err := git("update-ref", "-d", "refs/jci/"+info.Commit); err != nil {
			fmt.Printf("\n  Warning: failed to delete %s: %v\n", info.Commit[:12], err)
			continue
		}
		deleted++
	}
	fmt.Println() // newline after progress

	// Run gc to actually free space
	fmt.Println("Running git gc...")
	exec.Command("git", "gc", "--prune=now", "--quiet").Run()

	fmt.Printf("\nDeleted %d CI result(s), freed approximately %s\n", deleted, formatSize(prunedSize))
	return nil
}

func pruneRemote(opts *PruneOptions) error {
	remote := opts.OnRemote

	fmt.Printf("Fetching CI refs from %s...\n", remote)

	// Get remote refs
	out, err := git("ls-remote", remote, "refs/jci/*")
	if err != nil {
		return fmt.Errorf("failed to list remote refs: %v", err)
	}

	if out == "" {
		fmt.Println("No CI results on remote")
		return nil
	}

	lines := strings.Split(out, "\n")
	var refInfos []RefInfo

	fmt.Println("Scanning remote CI results...")
	for i, line := range lines {
		if line == "" {
			continue
		}
		printProgress(i+1, len(lines), "Scanning")

		parts := strings.Fields(line)
		if len(parts) != 2 {
			continue
		}

		refName := parts[1]
		commit := strings.TrimPrefix(refName, "refs/jci/")

		info := RefInfo{
			Ref:    refName,
			Commit: commit,
		}

		// Fetch this specific ref to get its timestamp
		// We need to fetch it temporarily to inspect it
		exec.Command("git", "fetch", remote, refName+":"+refName, "--quiet").Run()

		timeStr, err := git("log", "-1", "--format=%ci", refName)
		if err == nil {
			info.Timestamp, _ = time.Parse("2006-01-02 15:04:05 -0700", timeStr)
		}

		info.Size = getRefSize(refName)
		refInfos = append(refInfos, info)
	}
	fmt.Println() // newline after progress

	// Filter refs to prune
	var toPrune []RefInfo
	var prunedSize int64
	var totalSize int64
	now := time.Now()

	for _, info := range refInfos {
		totalSize += info.Size
		shouldPrune := false

		// Check age if --older-than specified
		if opts.OlderThan > 0 && !info.Timestamp.IsZero() {
			age := now.Sub(info.Timestamp)
			if age > opts.OlderThan {
				shouldPrune = true
			}
		}

		if shouldPrune {
			toPrune = append(toPrune, info)
			prunedSize += info.Size
		}
	}

	if len(toPrune) == 0 {
		fmt.Println("Nothing to prune on remote")
		fmt.Printf("Total remote CI data: %s\n", formatSize(totalSize))
		return nil
	}

	// Show what will be pruned
	fmt.Printf("\nFound %d ref(s) to prune on %s:\n", len(toPrune), remote)
	for _, info := range toPrune {
		age := ""
		if !info.Timestamp.IsZero() {
			age = fmt.Sprintf(" (age: %s)", formatAge(now.Sub(info.Timestamp)))
		}
		fmt.Printf("  %s %s%s\n", info.Commit[:12], formatSize(info.Size), age)
	}

	fmt.Printf("\nTotal to free on remote: %s (of %s total)\n", formatSize(prunedSize), formatSize(totalSize))

	if !opts.Commit {
		fmt.Println("\n[DRY RUN] Use --commit to actually delete from remote")
		return nil
	}

	// Delete from remote using git push with delete refspec
	fmt.Println("\nDeleting from remote...")
	deleted := 0
	for i, info := range toPrune {
		printProgress(i+1, len(toPrune), "Deleting")
		// Push empty ref to delete
		_, err := git("push", remote, ":refs/jci/"+info.Commit)
		if err != nil {
			fmt.Printf("\n  Warning: failed to delete %s: %v\n", info.Commit[:12], err)
			continue
		}
		deleted++
	}
	fmt.Println() // newline after progress

	fmt.Printf("\nDeleted %d CI result(s) from %s, freed approximately %s\n", deleted, remote, formatSize(prunedSize))
	return nil
}

// getRefSize estimates the size of objects in a ref
func getRefSize(ref string) int64 {
	// Get the tree and estimate size
	out, err := exec.Command("git", "rev-list", "--objects", ref).Output()
	if err != nil {
		return 0
	}

	var totalSize int64
	for _, line := range strings.Split(string(out), "\n") {
		if line == "" {
			continue
		}
		parts := strings.Fields(line)
		if len(parts) == 0 {
			continue
		}
		obj := parts[0]
		sizeOut, err := exec.Command("git", "cat-file", "-s", obj).Output()
		if err == nil {
			size, _ := strconv.ParseInt(strings.TrimSpace(string(sizeOut)), 10, 64)
			totalSize += size
		}
	}
	return totalSize
}

// printProgress prints a progress bar
func printProgress(current, total int, label string) {
	width := 30
	percent := float64(current) / float64(total)
	filled := int(percent * float64(width))

	bar := strings.Repeat("█", filled) + strings.Repeat("░", width-filled)
	fmt.Printf("\r%s [%s] %d/%d (%.0f%%)", label, bar, current, total, percent*100)
}

// formatSize formats bytes as human-readable
func formatSize(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

// formatAge formats a duration as human-readable age
func formatAge(d time.Duration) string {
	days := int(d.Hours() / 24)
	if days >= 365 {
		years := days / 365
		return fmt.Sprintf("%dy", years)
	}
	if days >= 30 {
		months := days / 30
		return fmt.Sprintf("%dmo", months)
	}
	if days >= 7 {
		weeks := days / 7
		return fmt.Sprintf("%dw", weeks)
	}
	if days > 0 {
		return fmt.Sprintf("%dd", days)
	}
	hours := int(d.Hours())
	if hours > 0 {
		return fmt.Sprintf("%dh", hours)
	}
	return "<1h"
}
